import os
import requests as http_client
from celery import shared_task
from django.conf import settings
from .models import VideoAsset, CrowdAnalytics


@shared_task
def process_video_asset(video_asset_id):
    try:
        video_asset = VideoAsset.objects.get(id=video_asset_id)
    except VideoAsset.DoesNotExist:
        return f"VideoAsset {video_asset_id} not found."

    # Mark as processing
    video_asset.status = "PROCESSING"
    video_asset.progress_percent = 5
    video_asset.save()

    try:
        ml_worker_url = getattr(settings, "ML_WORKER_URL", None)
        video_path = video_asset.file_path.path

        if ml_worker_url:
            # ── PRODUCTION PATH ───────────────────────────────────────────────
            # Send the video file directly to ML Worker as a multipart upload.
            # No external storage service required.
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found at {video_path}")

            video_asset.progress_percent = 10
            video_asset.save(update_fields=["progress_percent"])

            with open(video_path, "rb") as video_file:
                response = http_client.post(
                    f"{ml_worker_url.rstrip('/')}/process",
                    files={"file": ("video.mp4", video_file, "video/mp4")},
                    data={"fps": 1},
                    timeout=600,  # 10 min timeout for long videos
                )
            response.raise_for_status()

            timeline_data = response.json().get("timeline")
            if not timeline_data:
                raise ValueError(
                    f"ML Worker returned no timeline data. Response: {response.text[:200]}"
                )

        else:
            # ── LOCAL / DEV PATH ──────────────────────────────────────────────
            # Run the ML pipeline directly in this Celery worker process.
            # This requires torch, retinaface, transformers to be installed locally.
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found at {video_path}")

            import sys
            sys.path.insert(0, str(settings.BASE_DIR))
            from offline_processor import OfflineAudienceAnalytics

            analytics = OfflineAudienceAnalytics(fps=1)

            def progress_callback(percent):
                video_asset.progress_percent = percent
                video_asset.save(update_fields=["progress_percent"])

            timeline_data = analytics.process_video(
                video_path, output_json=None, progress_callback=progress_callback
            )

            if not timeline_data:
                raise ValueError("No timeline data was generated.")

        # Save results to database (analytics stored in PostgreSQL — persists forever)
        CrowdAnalytics.objects.create(
            video_asset=video_asset,
            timeline_data=timeline_data,
        )

        video_asset.status = "COMPLETED"
        video_asset.progress_percent = 100
        video_asset.save()

        # ── Clean up video file from disk ─────────────────────────────────────
        # Results are now safely in PostgreSQL. The raw video file is no longer
        # needed and would waste Render's limited disk space if kept.
        if ml_worker_url and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except OSError:
                pass  # Non-critical: file cleanup failure shouldn't fail the task

        return f"Successfully processed VideoAsset {video_asset_id}"

    except Exception as e:
        video_asset.status = "FAILED"
        video_asset.save()
        return f"Failed processing VideoAsset {video_asset_id}: {str(e)}"
