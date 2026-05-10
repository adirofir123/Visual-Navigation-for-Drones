"""Pydantic models for exported reference-frame rows (JSON / CSV)."""

from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any, Iterable, Literal

from pydantic import BaseModel, Field

from app.geometry.local_coordinates import usable_pair_lat_lon
from app.telemetry.telemetry_schema import TelemetryRecord as TelemetryRecordModel

CSV_FIELD_ORDER: tuple[str, ...] = (
    "reference_id",
    "frame_index",
    "timestamp_seconds",
    "image_path",
    "telemetry_block_index",
    "drone_lat",
    "drone_lon",
    "rel_alt_m",
    "abs_alt_m",
    "manual_height_above_takeoff_m",
    "manual_camera_angle_deg",
    "local_x_m",
    "local_y_m",
    "feature_type",
    "feature_path",
    "feature_status",
)


class ReferenceFrameRecord(BaseModel):
    reference_id: str
    frame_index: int = Field(ge=0)
    timestamp_seconds: float
    image_path: str
    telemetry_block_index: int | None = None
    drone_lat: float | None = None
    drone_lon: float | None = None
    rel_alt_m: float | None = None
    abs_alt_m: float | None = None
    manual_height_above_takeoff_m: float | None = None
    manual_camera_angle_deg: float | None = None
    local_x_m: float | None = None
    local_y_m: float | None = None
    feature_type: Literal["none", "orb"]
    feature_path: str | None = None
    feature_status: str


class ReferenceDatasetSummary(BaseModel):
    reference_id: str
    generated_at_iso: str
    video_path: str
    srt_path: str
    output_dir: str
    fps: float | None
    frame_count: int | None
    duration_seconds: float | None
    video_probe_source: str
    stride_seconds: float
    sample_count: int
    origin_lat_deg: float | None
    origin_lon_deg: float | None
    rows_with_gps: int
    rows_missing_gps: int
    extract_orb: bool
    orb_frames_written: int = 0
    orb_keypoint_counts: list[int] = Field(default_factory=list)


def records_to_jsonable(records: Iterable[ReferenceFrameRecord]) -> list[dict[str, Any]]:
    return [r.model_dump() for r in records]


def write_reference_frames_json(path: Path, records: list[ReferenceFrameRecord]) -> None:
    path.write_text(json.dumps(records_to_jsonable(records), indent=2), encoding="utf-8")


def write_reference_frames_csv(path: Path, records: list[ReferenceFrameRecord]) -> None:
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(CSV_FIELD_ORDER), extrasaction="raise")
    writer.writeheader()
    for r in records:
        dumped = r.model_dump()
        row = {k: ("" if dumped[k] is None else dumped[k]) for k in CSV_FIELD_ORDER}
        writer.writerow(row)
    path.write_text(buf.getvalue(), encoding="utf-8")


def write_reference_summary_json(path: Path, summary: ReferenceDatasetSummary) -> None:
    path.write_text(json.dumps(summary.model_dump(), indent=2), encoding="utf-8")


def telemetry_to_drone_geo(
    rec: TelemetryRecordModel,
) -> tuple[float | None, float | None, float | None, float | None]:
    """Map TelemetryRecord fields to drone_lat/lon and rel/abs altimeters meters."""

    pair = usable_pair_lat_lon(rec.gps_lat, rec.gps_lon, rec.latitude, rec.longitude)
    lat = pair[0] if pair else None
    lon = pair[1] if pair else None

    rel_alt = getattr(rec, "rel_altitude", None)
    if rel_alt is None:
        rel_alt = getattr(rec, "rel_altitude_m", None)
    abs_alt = getattr(rec, "altitude_m", None)
    if abs_alt is None:
        abs_alt = getattr(rec, "gps_alt", None)
    return lat, lon, rel_alt, abs_alt
