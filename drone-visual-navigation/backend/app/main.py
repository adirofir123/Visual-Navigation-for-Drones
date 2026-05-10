"""
FastAPI application entry — inspection dashboard API (local only).

Loads optional CORS allowlist via env DRONE_NAV_CORS_ORIGINS (comma-separated URL prefixes).
Defaults to localhost Vite dev servers.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.flights import router as flights_router


def _split_origins() -> list[str]:
    raw = os.environ.get("DRONE_NAV_CORS_ORIGINS", "").strip()
    defaults = ["http://127.0.0.1:5173", "http://localhost:5173"]
    if not raw:
        return defaults
    return [o.strip() for o in raw.split(",") if o.strip()]


def create_app() -> FastAPI:
    app = FastAPI(title="Drone Visual Navigation Inspector", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_split_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(flights_router)

    @app.get("/api/health")
    def health():
        """Lightweight readiness probe for frontend / ops."""

        return {"status": "ok"}

    return app


app = create_app()
