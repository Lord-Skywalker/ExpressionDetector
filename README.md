# Offline Post-Event Audience Analytics Platform

A production-grade ML platform that ingests recorded event videos, processes them asynchronously with a dense-crowd face detector and Vision Transformer classifier, and generates detailed time-series crowd emotion analytics.

## Architecture

```
React Frontend  →  Django REST API  →  Celery Worker  →  ML Pipeline
                                ↕                              ↕
                          PostgreSQL / SQLite          RetinaFace + ViT
                                ↕
                              Redis
```

## Project Structure

```
expressiondetector/
├── core/                   # Django project settings, URLs, Celery app
│   ├── celery.py           # Celery application entrypoint
│   ├── settings.py         # Django + Celery + DB configuration
│   └── urls.py             # Root URL router
├── analytics/              # Django app
│   ├── models.py           # Event, VideoAsset, CrowdAnalytics schemas
│   ├── serializers.py      # DRF serializers
│   ├── views.py            # API views (upload, status, analytics)
│   ├── urls.py             # App-level URL routes
│   └── tasks.py            # Celery task: process_video_asset
├── offline_processor.py    # ML pipeline (RetinaFace + ViT)
├── docker-compose.yml      # PostgreSQL + Redis services
└── requirements.txt        # All dependencies
```

## Setup & Running

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Infrastructure (requires Docker)
```bash
docker compose up -d
```
> Without Docker, the app falls back to SQLite (default dev config).

### 3. Apply Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Start Django API Server (Terminal 1)
```bash
python manage.py runserver
```

### 5. Start Celery Worker (Terminal 2)
```bash
celery -A core worker --loglevel=info
```

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `GET/POST` | `/api/events/` | List or create events |
| `GET` | `/api/videos/` | List all video assets |
| `POST` | `/api/videos/upload/` | Upload a video, trigger processing |
| `GET` | `/api/videos/<id>/status/` | Poll processing status + analytics |
| `GET` | `/api/analytics/<id>/` | Retrieve full time-series JSON |

### Upload a Video (Example)
```bash
curl -X POST http://localhost:8000/api/videos/upload/ \
  -F "event=1" \
  -F "file_path=@/path/to/concert.mp4"
```

### Poll Status
```bash
curl http://localhost:8000/api/videos/1/status/
```

## Analytics JSON Output Format

```json
[
  {
    "timestamp": 1.0,
    "total_faces": 42,
    "emotions_raw": {
      "angry": 3, "disgust": 1, "fear": 2,
      "happy": 28, "neutral": 5, "sad": 2, "surprise": 1
    },
    "emotions_percentage": {
      "angry": 7.14, "disgust": 2.38, "fear": 4.76,
      "happy": 66.67, "neutral": 11.9, "sad": 4.76, "surprise": 2.38
    }
  }
]
```

## ML Pipeline

- **Face Detector**: RetinaFace (InsightFace) — optimised for dense, overlapping crowds
- **Emotion Classifier**: `mrm8488/vit-base-patch16-224-finetuned-emotion` (Vision Transformer fine-tuned on FER2013)
- **Processing Rate**: 1 FPS (configurable via `--fps` argument)
