"""
Django views for the analytics app.

Live detection endpoints (/api/live/detect/, /api/live/classify/) load
ML models lazily via a singleton. In production, these endpoints are not
called — the React frontend calls the HuggingFace Space directly instead.
ML imports are wrapped in a try/except so the Django process on Render
(which does not have torch/transformers installed) doesn't crash on startup.
"""

import base64
import cv2
import numpy as np

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.conf import settings

from .models import Event, VideoAsset, CrowdAnalytics
from .serializers import (
    EventSerializer,
    VideoAssetSerializer,
    VideoAssetDetailSerializer,
    CrowdAnalyticsSerializer,
)
from .tasks import process_video_asset

# ── Live ML models (optional — only available when torch is installed) ────────

try:
    import torch
    from PIL import Image
    from transformers import ViTImageProcessor, ViTForImageClassification
    _LIVE_ML_AVAILABLE = True
except ImportError:
    _LIVE_ML_AVAILABLE = False


class LiveModelSingleton:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model_name = "afurkank/vit-face-expression"
            processor = ViTImageProcessor.from_pretrained(model_name)
            model = ViTForImageClassification.from_pretrained(model_name).to(device)
            model.eval()
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            cls._instance = {
                "processor": processor,
                "model": model,
                "device": device,
                "face_cascade": face_cascade,
            }
        return cls._instance


def _live_ml_unavailable_response():
    """Return a 503 when live ML is not available (production: use ML_WORKER_URL instead)."""
    ml_worker_url = getattr(settings, "ML_WORKER_URL", None)
    return Response(
        {
            "error": "Live ML is not available on this server.",
            "ml_worker_url": ml_worker_url,
            "hint": "Call the ML Worker directly for live detection.",
        },
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


# ── Live Emotion Detection ────────────────────────────────────────────────────

class LiveEmotionDetectionView(APIView):
    """
    POST /api/live/detect/
    Accepts a base64 encoded image frame in JSON:
      { "image": "data:image/jpeg;base64,..." }
    Runs fast face detection (Haar Cascade) + ViT classification.

    NOTE: In production, the React frontend calls the ML_WORKER_URL directly.
    This endpoint is used in local development only.
    """
    def post(self, request):
        if not _LIVE_ML_AVAILABLE:
            return _live_ml_unavailable_response()

        img_b64 = request.data.get("image")
        if not img_b64:
            return Response({"error": "No image data provided"}, status=status.HTTP_400_BAD_REQUEST)

        if "," in img_b64:
            img_b64 = img_b64.split(",")[1]

        try:
            img_bytes = base64.b64decode(img_b64)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img_bgr is None:
                raise ValueError("Decoded image is empty")
        except Exception as e:
            return Response({"error": f"Failed to decode image: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        singleton = LiveModelSingleton.get_instance()
        face_cascade = singleton["face_cascade"]
        processor = singleton["processor"]
        model = singleton["model"]
        device = singleton["device"]

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        faces_detected = face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )

        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        h_img, w_img, _ = img_rgb.shape

        faces_results = []
        for (x, y, w, h) in faces_detected:
            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(w_img, x + w), min(h_img, y + h)

            if (x2 - x1) < 15 or (y2 - y1) < 15:
                continue

            crop_img = img_rgb[y1:y2, x1:x2]
            try:
                pil_img = Image.fromarray(crop_img)
                inputs = processor(images=pil_img, return_tensors="pt").to(device)
                with torch.no_grad():
                    outputs = model(**inputs)
                    logits = outputs.logits
                    probs = torch.nn.functional.softmax(logits, dim=-1)[0]
                    predicted_class_idx = logits.argmax(-1).item()
                    label_map = model.config.id2label
                    dominant_emotion = label_map[predicted_class_idx].lower()
                    dominant_score = float(probs[predicted_class_idx].item() * 100)
                    all_emotions = {
                        label_map[i].lower(): float(p.item() * 100)
                        for i, p in enumerate(probs)
                    }
                faces_results.append({
                    "box": [int(x), int(y), int(w), int(h)],
                    "emotion": dominant_emotion,
                    "score": dominant_score,
                    "emotions": all_emotions,
                })
            except Exception as e:
                print(f"[!] Live inference error: {e}")

        return Response({"faces": faces_results}, status=status.HTTP_200_OK)


class LiveEmotionClassificationView(APIView):
    """
    POST /api/live/classify/
    Accepts base64 encoded cropped face image in JSON:
      { "image": "data:image/jpeg;base64,..." }
    Runs ViT model classification directly on the crop.

    NOTE: In production, the React frontend calls the ML_WORKER_URL directly.
    """
    def post(self, request):
        if not _LIVE_ML_AVAILABLE:
            return _live_ml_unavailable_response()

        img_b64 = request.data.get("image")
        if not img_b64:
            return Response({"error": "No image data provided"}, status=status.HTTP_400_BAD_REQUEST)

        if "," in img_b64:
            img_b64 = img_b64.split(",")[1]

        try:
            img_bytes = base64.b64decode(img_b64)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img_bgr is None:
                raise ValueError("Decoded image is empty")
        except Exception as e:
            return Response({"error": f"Failed to decode image: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        singleton = LiveModelSingleton.get_instance()
        processor = singleton["processor"]
        model = singleton["model"]
        device = singleton["device"]

        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        try:
            pil_img = Image.fromarray(img_rgb)
            inputs = processor(images=pil_img, return_tensors="pt").to(device)
            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits
                probs = torch.nn.functional.softmax(logits, dim=-1)[0]
                predicted_class_idx = logits.argmax(-1).item()
                label_map = model.config.id2label
                dominant_emotion = label_map[predicted_class_idx].lower()
                dominant_score = float(probs[predicted_class_idx].item() * 100)
                all_emotions = {
                    label_map[i].lower(): float(p.item() * 100)
                    for i, p in enumerate(probs)
                }
            return Response(
                {"emotion": dominant_emotion, "score": dominant_score, "emotions": all_emotions},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            print(f"[!] Live classification error: {e}")
            return Response(
                {"error": f"Model inference failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ── CRUD Views ────────────────────────────────────────────────────────────────

class EventListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/events/  - List all events.
    POST /api/events/  - Create a new event.
    """
    queryset = Event.objects.all().order_by("-created_at")
    serializer_class = EventSerializer


class VideoAssetUploadView(APIView):
    """
    POST /api/videos/upload/
    Accepts a multipart form upload with fields:
      - event (Event ID)
      - file_path (the .mp4 file)

    Saves the video, creates a VideoAsset with status=PENDING,
    then immediately dispatches the Celery background job.
    """
    def post(self, request):
        serializer = VideoAssetSerializer(data=request.data)
        if serializer.is_valid():
            video_asset = serializer.save(status="PENDING")
            process_video_asset.delay(video_asset.id)
            return Response(
                {
                    "message": "Video uploaded successfully. Processing has been queued.",
                    "video_asset": VideoAssetSerializer(video_asset).data,
                },
                status=status.HTTP_202_ACCEPTED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VideoAssetStatusView(generics.RetrieveAPIView):
    """
    GET /api/videos/<id>/status/
    Returns the current processing status and, once completed,
    the full nested analytics payload.
    """
    queryset = VideoAsset.objects.all()
    serializer_class = VideoAssetDetailSerializer


class VideoAssetListView(generics.ListAPIView):
    """
    GET /api/videos/
    Returns all video assets, optionally filtered by event.
    """
    serializer_class = VideoAssetSerializer

    def get_queryset(self):
        qs = VideoAsset.objects.all().order_by("-uploaded_at")
        event_id = self.request.query_params.get("event")
        if event_id:
            qs = qs.filter(event_id=event_id)
        return qs


class CrowdAnalyticsDetailView(generics.RetrieveAPIView):
    """
    GET /api/analytics/<video_asset_id>/
    Returns the full time-series analytics JSON for a completed video.
    """
    serializer_class = CrowdAnalyticsSerializer

    def get_object(self):
        video_asset = get_object_or_404(VideoAsset, pk=self.kwargs["pk"])
        return get_object_or_404(CrowdAnalytics, video_asset=video_asset)
