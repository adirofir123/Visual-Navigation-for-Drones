"""Local filesystem layout for per-flight raw, processed, and export artifacts."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import uuid


@dataclass(frozen=True)
class FlightPaths:
    """Resolved paths for one flight_id under DATA_DIR."""

    flight_id: str
    root: Path
    raw_dir: Path
    processed_dir: Path
    exports_dir: Path
    video_path: Path
    srt_path: Path
    dat_path: Path
    telemetry_json: Path
    summary_json: Path
    video_metadata_json: Path
    flight_metadata_json: Path
    export_csv: Path
    export_kml: Path


class FlightStorage:
    """
    input: base data directory (default from env DRONE_NAV_DATA_DIR or ./data).
    output: UUID flight folders and path helpers.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        env = os.environ.get("DRONE_NAV_DATA_DIR", "").strip()
        self.base = Path(base_dir or env or "data").resolve()

    def flights_root(self) -> Path:
        return self.base / "flights"

    def new_flight_id(self) -> str:
        return str(uuid.uuid4())

    def paths_for(self, flight_id: str, *, stored_video_name: str) -> FlightPaths:
        root = self.flights_root() / flight_id
        raw = root / "raw"
        proc = root / "processed"
        exp = root / "exports"
        return FlightPaths(
            flight_id=flight_id,
            root=root,
            raw_dir=raw,
            processed_dir=proc,
            exports_dir=exp,
            video_path=raw / stored_video_name,
            srt_path=raw / "telemetry.srt",
            dat_path=raw / "flight.dat",
            telemetry_json=proc / "telemetry.json",
            summary_json=proc / "summary.json",
            video_metadata_json=proc / "video_metadata.json",
            flight_metadata_json=proc / "flight_metadata.json",
            export_csv=exp / "telemetry.csv",
            export_kml=exp / "path.kml",
        )

    def ensure_layout(self, p: FlightPaths) -> None:
        p.raw_dir.mkdir(parents=True, exist_ok=True)
        p.processed_dir.mkdir(parents=True, exist_ok=True)
        p.exports_dir.mkdir(parents=True, exist_ok=True)


def derive_stored_video_name(original_name: str) -> str:
    """
    Stored filename strategy: preserve container extension; normalize to lowercase.

    input: client original filename string.
    output: `video.mp4`-style basename under raw/.
    """
    suffix = Path(original_name).suffix.lower() or ".mp4"
    return f"video{suffix}"
