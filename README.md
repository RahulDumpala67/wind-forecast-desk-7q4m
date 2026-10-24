# Northstar Wind Desk

A first-version decision-support dashboard for UK national wind generation. It compares Elexon BMRS wind forecasts available by a day-ahead decision cutoff with half-hourly actual wind generation for January 2026.

## Scope and calculations

- Actual generation is read from Elexon `FUELHH`, filtered to `fuelType = WIND`.
- Forecasts are read from Elexon `WINDFOR`.
- Select a delivery date from 1–31 January 2026 and a UK-local decision cutoff.
- For each delivery period, the API chooses the latest forecast `publishTime` at or before the cutoff. The default cutoff is 12:00 UK time on the preceding day.
- Error is `forecast − actual`; positive bias means over-forecasting. MAE is mean absolute error in MW across matched half-hours.
- Missing records remain blank and are excluded from paired metrics. This pilot does not calculate demand or recommend trades.

## Run locally with Docker

Requirements: Docker Desktop and Docker Compose.

```bash
docker compose up --build
```

Open <http://localhost:5173>. The API health endpoint is <http://localhost:8000/api/health>. Stop with `Ctrl+C` and optionally run `docker compose down`.

## Deploy on Vercel

The repository root `main.py` exposes the FastAPI application and serves the prebuilt React files from `frontend/dist`. Vercel detects the FastAPI app and installs the root `requirements.txt`. The React build is committed so a separate Node build step is not needed.

Vercel URL: https://wind-forecast-desk-7q4m.vercel.app

## Local development without Docker

Backend (Python 3.11+):

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Frontend (Node 20+), in another terminal:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

The Vite development proxy targets `http://localhost:8000` by default. Docker Compose overrides this with the backend service URL.

## Repository layout

- `backend/main.py` — FastAPI endpoints, Elexon requests, time-zone handling, forecast selection, and accuracy metrics.
- `backend/requirements.txt` — Backend dependencies for Docker/local development.
- `backend/Dockerfile` — Python API image.
- `frontend/src/main.jsx` — React dashboard, charts, table, CSV export, and controls.
- `frontend/src/style.css` — Dashboard styling and responsive layout.
- `frontend/index.html` — Frontend HTML entry point and metadata.
- `frontend/package.json` and `frontend/package-lock.json` — Frontend dependencies/scripts and lockfile.
- `frontend/vite.config.js` — Vite setup and local API proxy.
- `frontend/Dockerfile` — Frontend development image.
- `frontend/dist/` — Built frontend served by the root FastAPI app for Vercel.
- `main.py` — Vercel FastAPI entry point; also serves the built frontend.
- `requirements.txt` — Root dependencies used by Vercel.
- `docker-compose.yml` — Local frontend and backend services.

## Data notes

The backend requests the public Elexon BMRS API at `https://data.elexon.co.uk/bmrs/api/v1`. Upstream failures are reported in the UI; the app does not substitute demo values. Elexon can return incomplete history or be temporarily unavailable. Validate historical forecast retrieval and cutoff behavior before using this pilot for trading.

- [FUELHH documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream)
- [WINDFOR documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream)

## AI assistance

OpenAI Codex was used to assist with product decomposition, implementation, and README drafting. Review the API behavior and calculations before production use.

