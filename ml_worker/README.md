---
title: ExpressionDetector ML Worker
emoji: 🎭
colorFrom: purple
colorTo: indigo
sdk: docker
pinned: false
---

# ExpressionDetector ML Worker

A FastAPI service that runs the full ML pipeline for the ExpressionDetector platform:
- **Video Processing**: RetinaFace face detection + ViT emotion classification (offline batch)
- **Live Detection**: Real-time per-frame emotion analysis

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Keepalive / health check |
| `POST` | `/process` | Process a video from a URL, returns timeline JSON |
| `POST` | `/live/detect` | Detect faces + classify emotions in a base64 image frame |
| `POST` | `/live/classify` | Classify emotion in a single cropped face (base64) |
