# Drone visual navigation — milestone 1 (local inspector)

Local-only dashboard for inspecting drone recordings **with paired DJI-style SRT telemetry**. Upload an MP4/MOV plus its `.srt`, then explore synchronized video playback, GPS path (OpenStreetMap / Leaflet), structured telemetry fields, raw cue text, and exports (CSV / KML / JSON). No cloud upload, no Google Maps key, and **no VO / matching / DPVO / LightGlue** in this milestone—only hooks and storage layout for later experiments.

## Features

- Multipart ingest → `data/flights/{flight_id}/` with raw, processed JSON, and export sidecars.
- HTML5 `<video>` streaming from FastAPI (`GET /api/flights/{id}/video`).
- DJI-ish SRT parser with **GPS(lon,lat,alt)** ordering preserved for KML `lon,lat,alt`.
- Map polyline + start / end markers + synced “current” marker.
- Telemetry sidebar with `N/A` for missing fields; collapsible raw block + exports.
- Automated tests (`pytest`, `vitest`).

## Repository layout

```
drone-visual-navigation/
  backend/            # FastAPI service
  frontend/           # Vite + React + TypeScript UI
  data/flights/       # Local uploads (gitignored)
  scripts/run_local.sh
```

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** (npm)
- Optional but recommended: **FFmpeg/ffprobe** on `PATH` for richer video metadata (falls back to OpenCV).

## Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Set the data directory when running from nested folders (automatic in `scripts/run_local.sh`):

```bash
export DRONE_NAV_DATA_DIR="$(pwd)/../data"        # POSIX
# PowerShell example:
# $env:DRONE_NAV_DATA_DIR = "$(Resolve-Path ..\\data)"
```

Run the API:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### API quick reference

| Method | Path | Notes |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness JSON |
| `POST` | `/api/flights/upload` | Multipart fields `video`, `srt` |
| `GET` | `/api/flights/{id}/video` | Streamed media for `<video>` |
| `GET` | `/api/flights/{id}/telemetry` | Processed telemetry + summary |
| `GET` | `/api/flights/{id}/exports/csv` | Flattened CSV |
| `GET` | `/api/flights/{id}/exports/kml` | Google Earth LineString (`lon,lat,alt`) |
| `GET` | `/api/flights/{id}/exports/json` | Parsed telemetry JSON |

CORS defaults to `http://127.0.0.1:5173` and `http://localhost:5173`. Override with comma-separated `DRONE_NAV_CORS_ORIGINS`.

## Frontend setup

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Configure the API base (defaults to `http://127.0.0.1:8000`):

```bash
echo VITE_API_BASE=http://127.0.0.1:8000 > .env.local
```

Run unit tests:

```bash
npm run test
```

## One-command local start

From the repository root (Git Bash / WSL / macOS):

```bash
chmod +x scripts/run_local.sh   # once
./scripts/run_local.sh
```

`run_local.sh` must use **Unix (LF)** line endings. If you ever see **`/usr/bin/env: ‘bash\r’: No such file or directory`** under WSL, run `sed -i 's/\r$//' scripts/run_local.sh`. This repo includes **`.gitattributes`** so `*.sh` check out with LF on Windows hosts.

### WSL (same repo accessed from `/mnt/c/...`)

- **Backend:** The script ensures **`backend/.venv`** exists, runs **`pip install -r requirements.txt`**, and starts **`python -m uvicorn`** from that venv (avoids **`No module named 'fastapi'`** when the distro’s system Python has no project deps).
- **Frontend:** If you previously ran **`npm install` on native Windows**, open **`node_modules` from WSL and Rollup misses **`@rollup/rollup-*-linux*`**. The script detects that mismatch and reinstalls **`node_modules` under Linux** before **`npm run dev`**.

The script exports `DRONE_NAV_DATA_DIR` to `./data`, boots Uvicorn on **8000** and Vite on **5173**, and prints both URLs.

**Windows PowerShell (manual two terminals):**

```powershell
$env:DRONE_NAV_DATA_DIR = "$PWD\data"
cd backend; .\.venv\Scripts\activate; uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
cd frontend; npm run dev -- --host 127.0.0.1 --port 5173
```

## Using the UI

1. Open the printed Vite URL.
2. Choose **Video** + **SRT** files.
3. Click **Load flight** — a loading overlay covers upload + server-side parsing.
4. Play / seek the video; the map marker and telemetry panel track the nearest SRT cue midpoint (`src/domain/sync.ts`).
5. Expand **Raw telemetry block** for cue text + export buttons.
6. Download **KML** and open it in Google Earth (desktop or web) — no Google Earth install is required for the viewer itself.

## Exports & Google Earth

- `GET /api/flights/{flight_id}/exports/kml` writes coordinates as **`longitude,latitude,altitude`** per KML rules; rows without GPS are skipped.
- Google Earth is only needed to **view** the exported path, not to run the dashboard.

## Known limitations

- **HTTP Range / seeking:** video is served via `FileResponse`. Most browsers handle basic streaming, but exotic codecs or aggressive caching may require explicit `Content-Range` handling—see `backend/app/video/video_streaming.py` TODO.
- **SRT variability:** DJI firmware revisions differ; the parser is regex-tolerant but cannot guarantee every field for every drone.
- **Sync model:** nearest cue midpoint with a default 2.5 s gap threshold—good enough for inspection, not ground-truth geodesy.
- **Upload progress:** the UI shows a blocking loader; byte-level progress is intentionally omitted to keep the client simple.

## Tests

```bash
cd backend
pytest app/tests -q
```

```bash
cd frontend
npm run test
```

## Future milestones (not implemented here)

Planned research extensions enabled by this storage/processing split:

- Center-point projection & global anchor frames
- Reference frame / map tile databases
- Deep feature matching (e.g. LightGlue) and loop closure
- DPVO / learned drift correction for GNSS-denied navigation

Keep heavy algorithms out of the FastAPI routes—extend `data/flights/{id}/processed/` and dedicated Python packages when those milestones begin.
