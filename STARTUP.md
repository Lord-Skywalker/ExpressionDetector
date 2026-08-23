# 🚀 Project Startup Guide

> **For humans and AI agents**: This file contains everything needed to understand and start the ExpressionDetector project from scratch.

---

## What This Project Is

An **Offline Post-Event Audience Analytics Platform** that:
- Accepts uploaded event videos via a REST API
- Asynchronously processes them through an ML pipeline (RetinaFace face detector + ViT emotion classifier)
- Returns time-series crowd emotion analytics (emotions per second, percentages, face counts)
- Displays results in a React dashboard with charts

**Stack**: Django REST API + Celery (filesystem broker) + React/Vite frontend + SQLite

---

## Project Structure

```
expressiondetector/
├── core/               # Django project (settings, URLs, Celery config)
├── analytics/          # Django app (models, views, serializers, Celery tasks)
├── offline_processor.py# ML pipeline: RetinaFace + ViT
├── frontend/           # React + Vite frontend (port 5173)
├── broker/out/         # Celery filesystem broker queue directory
├── media/              # Uploaded video files (auto-created)
├── venv/               # Python virtual environment
├── manage.py
├── requirements.txt
└── start.ps1           # One-command startup script (Windows PowerShell)
```

---

## Prerequisites

- Python virtual environment at `venv/` (already created)
- Node.js + npm installed
- **No Docker/Redis needed** — Celery uses filesystem broker

---

## Starting the Project

### Option A — One Script (Recommended)

Run this from the project root in PowerShell:

```powershell
.\start.ps1
```

This opens 3 terminal windows automatically:
1. Django API server → http://localhost:8000
2. Celery worker (filesystem broker)
3. React/Vite frontend → http://localhost:5173

---

### Option B — Manually (3 separate terminals)

**Terminal 1 — Django API server:**
```powershell
cd d:\CODES\expressiondetector
.\venv\Scripts\python.exe manage.py runserver
```

**Terminal 2 — Celery worker:**
```powershell
cd d:\CODES\expressiondetector
.\venv\Scripts\celery.exe -A core worker --loglevel=info --pool=solo
```

**Terminal 3 — React frontend:**
```powershell
cd d:\CODES\expressiondetector\frontend
npm run dev
```

---

## First-Time Setup (only needed once)

If you're setting up on a new machine:

```powershell
# 1. Create virtual environment
python -m venv venv

# 2. Install Python dependencies
.\venv\Scripts\pip.exe install -r requirements.txt

# 3. Apply database migrations
.\venv\Scripts\python.exe manage.py migrate

# 4. Create broker directory
New-Item -ItemType Directory -Path broker\out -Force

# 5. Install frontend dependencies
cd frontend
npm install
cd ..
```

---

## Service URLs

| Service        | URL                          |
|----------------|------------------------------|
| React Frontend | http://localhost:5173         |
| Django API     | http://localhost:8000/api/   |
| Django Admin   | http://localhost:8000/admin/ |

---

## Key API Endpoints

| Method     | Endpoint                     | Description                        |
|------------|------------------------------|------------------------------------|
| GET/POST   | `/api/events/`               | List or create events              |
| POST       | `/api/videos/upload/`        | Upload a video, trigger processing |
| GET        | `/api/videos/<id>/status/`   | Poll processing status + progress  |
| GET        | `/api/analytics/<id>/`       | Retrieve full time-series JSON     |
| POST       | `/api/live/detect/`          | Live emotion detection (frame)     |

---

## Important Config Notes

- **Database**: SQLite (`db.sqlite3`) — already migrated, no setup needed
- **Celery broker**: `filesystem://` — uses `broker/out/` folder, no Redis required
- **CORS**: Allows `localhost:3000` and `localhost:5173` (React dev server)
- **Media files**: Uploaded videos stored in `media/` folder
- **ML models**: Downloaded automatically on first use by `transformers` / `insightface`

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `broker/out` not found error | Run `New-Item -ItemType Directory -Path broker\out -Force` |
| Port 8000 already in use | `netstat -ano \| findstr :8000` then kill the PID |
| Port 5173 already in use | Vite auto-picks next free port, check terminal output |
| Celery tasks not processing | Make sure `broker/out/` exists and Celery worker is running |
| ML models slow on first run | Models download from HuggingFace — wait a few minutes |

---

## For AI Agents

To start this project, run these commands in order:

```powershell
# Step 1: Ensure broker directory exists
New-Item -ItemType Directory -Path "d:\CODES\expressiondetector\broker\out" -Force

# Step 2: Run any pending migrations
d:\CODES\expressiondetector\venv\Scripts\python.exe d:\CODES\expressiondetector\manage.py migrate

# Step 3: Start Django (background daemon)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd d:\CODES\expressiondetector; .\venv\Scripts\python.exe manage.py runserver"

# Step 4: Start Celery worker (background daemon)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd d:\CODES\expressiondetector; .\venv\Scripts\celery.exe -A core worker --loglevel=info --pool=solo"

# Step 5: Start React frontend (background daemon)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd d:\CODES\expressiondetector\frontend; npm run dev"
```

All services should be ready within ~10 seconds. Open http://localhost:5173 in a browser.
