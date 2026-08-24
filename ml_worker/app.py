"""
ExpressionDetector ML Worker
=============================
FastAPI service exposing the full ML pipeline:
  - POST /process        → batch video processing (MTCNN + ViT)
  - POST /live/detect    → real-time frame detection (MTCNN + ViT)
  - POST /live/classify  → classify a single cropped face (ViT only)
  - GET  /health         → keepalive / health check

Uses PyTorch exclusively (facenet-pytorch MTCNN for face detection,
ViT for emotion classification). No TensorFlow dependency.
"""

import base64
import os
import tempfile
import warnings
import threading

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

warnings.filterwarnings("ignore")

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ExpressionDetector ML Worker",
    description="MTCNN + ViT emotion analysis pipeline",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Singleton model loader ────────────────────────────────────────────────────

class ModelSingleton:
    """Loads all ML models once and keeps them in memory. PyTorch only."""

    _pipeline = None
    _live_models = None
    _lock = threading.Lock()

    @classmethod
    def get_pipeline(cls):
        if cls._pipeline is None:
            print("[*] Loading OfflineAudienceAnalytics pipeline...")
            from offline_processor import OfflineAudienceAnalytics
            # Load live models first (self-locking) — pipeline reuses them
            live_models = cls.get_live_models()
            with cls._lock:
                if cls._pipeline is None:  # Double-checked locking
                    cls._pipeline = OfflineAudienceAnalytics(fps=1, preloaded_models=live_models)
                    print("[✓] Pipeline ready.")
        return cls._pipeline

    @classmethod
    def get_live_models(cls) -> dict:
        with cls._lock:
            if cls._live_models is None:
                print("[*] Loading live detection models (PyTorch only)...")
                import torch
                print(f"[DEBUG] torch version: {torch.__version__}")

                from transformers.models.vit.modeling_vit import ViTForImageClassification
                from transformers.models.vit.image_processing_vit import ViTImageProcessor
                from facenet_pytorch import MTCNN

                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                print(f"[DEBUG] Device: {device}")

                # ViT emotion classifier
                model_name = "afurkank/vit-face-expression"
                processor = ViTImageProcessor.from_pretrained(model_name)
                model = ViTForImageClassification.from_pretrained(model_name).to(device)
                model.eval()
                print("[DEBUG] ViT model loaded.")

                # MTCNN face detector (PyTorch — replaces RetinaFace/TensorFlow)
                mtcnn = MTCNN(
                    keep_all=True,
                    device=device,
                    min_face_size=20,
                    thresholds=[0.6, 0.7, 0.7],
                    post_process=False,
                )
                print("[DEBUG] MTCNN loaded.")

                cls._live_models = {
                    "processor": processor,
                    "model": model,
                    "device": device,
                    "mtcnn": mtcnn,
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


def detect_faces_mtcnn(img_bgr: np.ndarray, models: dict) -> list:
    """
    Run MTCNN face detection on a BGR image.
    Returns list of dicts with 'box' [x, y, w, h] and face crop.
    """
    from PIL import Image

    mtcnn = models["mtcnn"]
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    h_img, w_img = img_rgb.shape[:2]
    pil_img = Image.fromarray(img_rgb)

    boxes, probs = mtcnn.detect(pil_img)

    results = []
    if boxes is None:
        return results

    for box, prob in zip(boxes, probs):
        if prob is None or prob < 0.85:
            continue
        x1, y1, x2, y2 = [int(v) for v in box]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w_img, x2), min(h_img, y2)
        if (x2 - x1) < 15 or (y2 - y1) < 15:
            continue
        crop_rgb = img_rgb[y1:y2, x1:x2]
        results.append({
            "box": [x1, y1, x2 - x1, y2 - y1],
            "crop_rgb": crop_rgb,
        })

    return results


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """
    Keepalive endpoint. Triggers model loading in background if not already loaded.
    """
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
    Accept a video file upload from the Django Celery worker.
    Runs full MTCNN + ViT pipeline and returns timeline JSON.
    """
    print(f"[DEBUG] Received /process request. File: {file.filename}, FPS: {fps}")
    pipeline = ModelSingleton.get_pipeline()

    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            print("[DEBUG] Reading uploaded file...")
            content = await file.read()
            print(f"[DEBUG] File size: {len(content)} bytes. Writing to disk...")
            f.write(content)
            tmp_path = f.name
            print(f"[DEBUG] Saved to: {tmp_path}")
    except Exception as e:
        print(f"[!] Failed to save uploaded file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to save uploaded file: {str(e)}")

    try:
        print("[DEBUG] Starting pipeline.process_video...")
        timeline_data = pipeline.process_video(tmp_path, output_json=None)
        print(f"[DEBUG] Pipeline finished! {len(timeline_data) if timeline_data else 0} timeline entries.")
        if not timeline_data:
            raise HTTPException(status_code=422, detail="No timeline data generated — video may be empty or corrupt.")
        return {"timeline": timeline_data}
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/live/detect")
def live_detect(req: LiveDetectRequest):
    """
    Accepts a base64 encoded video frame.
    Runs MTCNN face detection + ViT emotion classification.
    Returns list of detected faces with bounding boxes and emotions.
    """
    models = ModelSingleton.get_live_models()

    try:
        img_bgr = decode_base64_image(req.image)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    faces = detect_faces_mtcnn(img_bgr, models)

    faces_results = []
    for face in faces:
        try:
            result = classify_face_crop(face["crop_rgb"], models)
            faces_results.append({
                "box": face["box"],
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
    """
    models = ModelSingleton.get_live_models()

    try:
        img_bgr = decode_base64_image(req.image)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    try:
        result = classify_face_crop(img_rgb, models)
        return result
    except Exception as e:
        print(f"[!] Live classification error: {e}")
        raise HTTPException(status_code=500, detail=f"Model inference failed: {str(e)}")
