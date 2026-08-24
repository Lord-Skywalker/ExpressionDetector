import cv2
import json
import os
import torch
from facenet_pytorch import MTCNN
from transformers.models.vit.image_processing_vit import ViTImageProcessor
from transformers.models.vit.modeling_vit import ViTForImageClassification
from PIL import Image
import numpy as np
from tqdm import tqdm
import math
import warnings
import gc

warnings.filterwarnings("ignore")


class OfflineAudienceAnalytics:
    def __init__(self, fps=1, preloaded_models=None):
        if preloaded_models:
            self.device = preloaded_models["device"]
            self.processor = preloaded_models["processor"]
            self.model = preloaded_models["model"]
            self.mtcnn = preloaded_models["mtcnn"]
            print(f"[*] Re-using preloaded ML Models on {self.device}...")
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            print(f"[*] Initializing ML Models on {self.device}...")

            # Load ViT for FER (Fine-tuned on FER2013)
            model_name = "afurkank/vit-face-expression"
            self.processor = ViTImageProcessor.from_pretrained(model_name)
            self.model = ViTForImageClassification.from_pretrained(model_name).to(
                self.device
            )
            self.model.eval()
            self.mtcnn = MTCNN(
                keep_all=True,
                device=self.device,
                min_face_size=20,
                thresholds=[0.6, 0.7, 0.7],
                post_process=False,
            )

        self.target_fps = fps  # Frames to process per second of video

    def process_video(self, video_path, output_json=None, progress_callback=None):
        print(f"[*] Starting offline processing for: {video_path}")

        if not os.path.exists(video_path):
            print(f"[!] Error: {video_path} not found.")
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"[!] Error: Could not open video {video_path}")
            return

        video_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_duration = total_frames / video_fps

        print(
            f"[*] Video Details: {video_fps:.2f} FPS, {total_frames} frames, ~{video_duration:.2f}s duration."
        )

        # Calculate frame skip
        frame_skip = int(math.ceil(video_fps / self.target_fps))

        timeline_data = []

        frame_idx = 0
        pbar = tqdm(total=total_frames, desc="Processing Frames")

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_skip == 0:
                print(f"[DEBUG] Processing frame {frame_idx}/{total_frames} (timestamp: {frame_idx / video_fps:.2f}s)")
                timestamp = frame_idx / video_fps

                print(f"[DEBUG] Analyzing frame {frame_idx}...")
                frame_data = self._analyze_frame(frame, timestamp)
                timeline_data.append(frame_data)

                print(f"[DEBUG] Frame {frame_idx} analyzed successfully.")
                if progress_callback and total_frames > 0:
                    percent = int((frame_idx / total_frames) * 100)
                    progress_callback(percent)

            frame_idx += 1
            pbar.update(1)

            # Force garbage collection to prevent memory leaks across frames
            if frame_idx % 10 == 0:
                gc.collect()

        pbar.close()
        cap.release()

        if progress_callback:
            progress_callback(100)

        # Save to JSON if path provided
        if output_json:
            with open(output_json, 'w') as f:
                json.dump(timeline_data, f, indent=4)
            print(f"[*] Analysis complete. Results saved to {output_json}")

        return timeline_data

    def _analyze_frame(self, frame_bgr, timestamp):
        # Resize frame to prevent massive memory spikes with high-res videos
        h, w = frame_bgr.shape[:2]
        max_width = 640
        if w > max_width:
            scale = max_width / float(w)
            new_h, new_w = int(h * scale), max_width
            frame_bgr = cv2.resize(frame_bgr, (new_w, new_h))

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        pil_frame = Image.fromarray(frame_rgb)

        # Detect faces using MTCNN
        try:
            boxes, probs = self.mtcnn.detect(pil_frame)
        except Exception as e:
            print(f"Error detecting faces at {timestamp}s: {e}")
            boxes = None
            probs = None

        emotion_counts = {
            "angry": 0,
            "disgust": 0,
            "fear": 0,
            "happy": 0,
            "neutral": 0,
            "sad": 0,
            "surprise": 0,
        }

        total_faces = 0

        if boxes is not None:
            for box, prob in zip(boxes, probs):
                if prob is None or prob < 0.85:
                    continue
                x1, y1, x2, y2 = [int(v) for v in box]

                # Ensure bounds
                h, w, _ = frame_rgb.shape
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)

                if x2 - x1 < 15 or y2 - y1 < 15:  # Skip extremely small crops (noise)
                    continue

                crop_img = frame_rgb[y1:y2, x1:x2]

                try:
                    pil_img = Image.fromarray(crop_img)
                    inputs = self.processor(images=pil_img, return_tensors="pt").to(
                        self.device
                    )

                    with torch.no_grad():
                        outputs = self.model(**inputs)
                        logits = outputs.logits
                        predicted_class_idx = logits.argmax(-1).item()
                        emotion = self.model.config.id2label[
                            predicted_class_idx
                        ].lower()

                        if emotion in emotion_counts:
                            emotion_counts[emotion] += 1
                        total_faces += 1
                except Exception as e:
                    pass

        # Calculate percentages
        emotion_percentages = {}
        for em, count in emotion_counts.items():
            emotion_percentages[em] = (
                round((count / total_faces * 100), 2) if total_faces > 0 else 0.0
            )

        return {
            "timestamp": round(timestamp, 2),
            "total_faces": total_faces,
            "emotions_raw": emotion_counts,
            "emotions_percentage": emotion_percentages,
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Offline Crowd Emotion Analytics Pipeline"
    )
    parser.add_argument(
        "--video", type=str, required=True, help="Path to input video file"
    )
    parser.add_argument(
        "--fps", type=int, default=1, help="Frames to process per second of video"
    )
    parser.add_argument(
        "--output", type=str, default="analytics.json", help="Path to output JSON"
    )

    args = parser.parse_args()

    analytics = OfflineAudienceAnalytics(fps=args.fps)
    analytics.process_video(args.video, args.output)
