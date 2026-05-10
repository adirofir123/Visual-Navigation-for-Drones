"""Flatten telemetry records to CSV bytes."""

from __future__ import annotations

import csv
import io
from typing import Any

from app.telemetry.telemetry_schema import TelemetryRecord


_CSV_COLUMNS: list[str] = [
    "block_index",
    "start_time_raw",
    "end_time_raw",
    "start_time_seconds",
    "end_time_seconds",
    "home_lon",
    "home_lat",
    "gps_lon",
    "gps_lat",
    "gps_alt",
    "latitude",
    "longitude",
    "altitude_m",
    "rel_altitude",
    "rel_altitude_m",
    "barometer",
    "iso",
    "shutter",
    "ev",
    "fnum",
    "gimbal_pitch_deg",
    "gimbal_roll_deg",
    "gimbal_yaw_deg",
    "yaw_deg",
    "heading_deg",
    "frame_count",
    "diff_time_ms",
    "capture_datetime",
    "color_md",
    "focal_len",
    "ct",
    "shutter_raw",
    "raw_text",
]


def telemetry_to_csv_bytes(records: list[TelemetryRecord]) -> bytes:
    """
    Serialize records to RFC4180-ish CSV UTF-8 with header.

    input: parsed telemetry list.
    output: UTF-8 encoded bytes suitable for FileResponse / download.
    """

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for r in records:
        row: dict[str, Any] = r.model_dump()
        writer.writerow(row)
    return buf.getvalue().encode("utf-8")
