"""
ExpressionDetector ML Worker — HuggingFace Space
=================================================
FastAPI service exposing the full ML pipeline:
  - POST /process        → batch video processing (RetinaFace + ViT)
                           Accepts direct file upload (no external storage needed)
  - POST /live/detect    → real-time frame detection (Haar Cascade + ViT)
  - POST /live/classify  → classify a single cropped face (ViT only)
  - GET  /health         → keepalive / health check

This service runs on HuggingFace Spaces (16 GB RAM free tier).
The Django Celery worker uploads the video file directly to /process.
The React frontend calls /live/detect and /live/classify directly.
"""

import base64
import os
import tempfile
import warnings

import cv2
import numpy as np
import cv2
import numpy as np
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

warnings.filterwarnings("ignore")

# ── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ExpressionDetector ML Worker",
    description="RetinaFace + ViT emotion analysis pipeline",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restricted by Django in production; open here for React
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Singleton model loader ────────────────────────────────────────────────────

class ModelSingleton:
    """Loads all ML models once at startup and keeps them in memory."""

    _pipeline = None
    _live_models = None

    @classmethod
    def get_pipeline(cls):
        if cls._pipeline is None:
            print("[*] Loading OfflineAudienceAnalytics pipeline...")
            from offline_processor import OfflineAudienceAnalytics
            cls._pipeline = OfflineAudienceAnalytics(fps=1)
            print("[✓] Pipeline ready.")
        return cls._pipeline

    @classmethod
    def get_live_models(cls) -> dict:
        if cls._live_models is None:
            print("[*] Loading live detection models...")
            import torch
            from transformers import ViTForImageClassification, ViTImageProcessor
            
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model_name = "afurkank/vit-face-expression"
            processor = ViTImageProcessor.from_pretrained(model_name)
            model = ViTForImageClassification.from_pretrained(model_name).to(device)
            model.eval()
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            cls._live_models = {
                "processor": processor,
                "model": model,
                "device": device,
                "face_cascade": face_cascade,
            }
            print(f"[✓] Live models loaded on {device}.")
        return cls._live_models


# ── Request / Response schemas ────────────────────────────────────────────────

class LiveDetectRequest(BaseModel):
    image: str  # base64 encoded image (data URL or raw base64)


class LiveClassifyRequest(BaseModel):
    image: str  # base64 encoded cropped face


# ── Helpers ───────────────────────────────────────────────────────────────────

def decode_base64_image(img_b64: str) -> np.ndarray:
    """Decode a base64 string (with or without data URL header) to a BGR numpy array."""
    if "," in img_b64:
        img_b64 = img_b64.split(",")[1]
    img_bytes = base64.b64decode(img_b64)
    nparr = np.frombuffer(img_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Failed to decode image — invalid base64 or format.")
    return img_bgr


def classify_face_crop(crop_rgb: np.ndarray, models: dict) -> dict:
    """Run ViT emotion classifier on a single RGB face crop."""
    import torch
    from PIL import Image
    
    processor = models["processor"]
    model = models["model"]
    device = models["device"]

    pil_img = Image.fromarray(crop_rgb)
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

    return {
        "emotion": dominant_emotion,
        "score": dominant_score,
        "emotions": all_emotions,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

import threading

@app.get("/health")
def health():
    """
    Keepalive endpoint — used for pre-warming.
    Triggers model loading in a background thread if not already loaded.
    """
    # Trigger loading in a background thread so the health check responds instantly
    # but still achieves the pre-warming effect for the models.
    def _warmup():
        try:
            ModelSingleton.get_live_models()
            ModelSingleton.get_pipeline()
        except Exception as e:
            print(f"[!] Pre-warming error: {e}")

    threading.Thread(target=_warmup, daemon=True).start()
    return {"status": "ok", "service": "expressiondetector-ml-worker", "warming": True}


@app.post("/process")
async def process_video(
    file: UploadFile = File(...),
    fps: int = Form(default=1),
):
    """
    Accept a video file upload directly from the Django Celery worker.
    Runs the full RetinaFace + ViT pipeline and returns timeline JSON.
    No external storage service required — the file is streamed directly.
    """
    pipeline = ModelSingleton.get_pipeline()

    # Save uploaded file to a temp location for processing
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            content = await file.read()
            f.write(content)
            tmp_path = f.name
    except Exception as e:
        return {"error": f"Failed to save uploaded file: {str(e)}"}, 400

    try:
        timeline_data = pipeline.process_video(tmp_path, output_json=None)
        if not timeline_data:
            return {"error": "No timeline data generated — video may be empty or corrupt."}, 422
        return {"timeline": timeline_data}
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/live/detect")
def live_detect(req: LiveDetectRequest):
    """
    Accepts a base64 encoded video frame.
    Runs Haar Cascade face detection + ViT emotion classification.
    Returns list of detected faces with bounding boxes and emotions.
    Called directly by the React frontend.
    """
    models = ModelSingleton.get_live_models()

    try:
        img_bgr = decode_base64_image(req.image)
    except Exception as e:
        return {"error": str(e)}, 400

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    faces_detected = models["face_cascade"].detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
    )

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    h_img, w_img, _ = img_rgb.shape

    faces_results = []
    for x, y, w, h in faces_detected if len(faces_detected) > 0 else []:
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(w_img, x + w), min(h_img, y + h)

        if (x2 - x1) < 15 or (y2 - y1) < 15:
            continue

        crop_rgb = img_rgb[y1:y2, x1:x2]
        try:
            result = classify_face_crop(crop_rgb, models)
            faces_results.append({
                "box": [int(x), int(y), int(w), int(h)],
                **result,
            })
        except Exception as e:
            print(f"[!] Live inference error on face crop: {e}")

    return {"faces": faces_results}


@app.post("/live/classify")
def live_classify(req: LiveClassifyRequest):
    """
    Accepts a base64 encoded cropped face image.
    Runs ViT emotion classifier directly on the crop.
    Called directly by the React frontend.
    """
    models = ModelSingleton.get_live_models()

    try:
        img_bgr = decode_base64_image(req.image)
    except Exception as e:
        return {"error": str(e)}, 400

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    try:
        result = classify_face_crop(img_rgb, models)
        return result
    except Exception as e:
        print(f"[!] Live classification error: {e}")
        return {"error": f"Model inference failed: {str(e)}"}, 500
