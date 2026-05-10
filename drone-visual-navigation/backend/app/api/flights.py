"""Flight upload, streaming, telemetry, and export endpoints."""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.geo.csv_exporter import telemetry_to_csv_bytes
from app.geo.kml_exporter import telemetry_to_kml_bytes
from app.storage.flight_storage import FlightStorage, derive_stored_video_name
from drone_nav.telemetry.srt_parser import (
    SrtParseError,
    build_fields_detected,
    build_summary,
    parse_dji_srt,
    records_to_jsonable,
)
from drone_nav.telemetry.telemetry_schema import FlightManualMetadata, FlightSummary
from app.video.video_metadata import extract_video_metadata
from app.video.video_streaming import video_file_response


router = APIRouter(prefix="/api/flights", tags=["flights"])


def get_storage() -> FlightStorage:
    return FlightStorage()


def _flight_dir_exists(storage: FlightStorage, flight_id: str) -> Path | None:
    root = storage.flights_root() / flight_id
    return root if root.is_dir() else None


def _invalidate_flight(paths_root: Path) -> None:
    if paths_root.is_dir():
        shutil.rmtree(paths_root, ignore_errors=True)


def _parse_manual_metadata_form(
    raw_height: str | None,
    raw_angle: str | None,
) -> FlightManualMetadata:
    """Interpret optional multipart strings; strip empties → null floats."""

    def norm(raw: str | None) -> str | None:
        if raw is None:
            return None
        out = raw.strip()
        return out if out else None

    nh = norm(raw_height)
    na = norm(raw_angle)
    height: float | None = None
    angle: float | None = None
    if nh is not None:
        try:
            height = float(nh.replace(",", "."))
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="manual_height_above_takeoff_m must be a valid number.",
            ) from exc
        if not math.isfinite(height):
            raise HTTPException(status_code=400, detail="manual_height_above_takeoff_m must be finite.")

    if na is not None:
        try:
            angle = float(na.replace(",", "."))
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="manual_camera_angle_deg must be a valid number.",
            ) from exc
        if not math.isfinite(angle):
            raise HTTPException(status_code=400, detail="manual_camera_angle_deg must be finite.")
        if not (0.0 <= angle <= 90.0):
            raise HTTPException(
                status_code=400,
                detail="manual_camera_angle_deg must be between 0 and 90 degrees.",
            )

    return FlightManualMetadata(
        manual_height_above_takeoff_m=height,
        manual_camera_angle_deg=angle,
    )


@router.post("/upload")
async def upload_flight(
    video: Annotated[UploadFile, File(...)],
    srt: Annotated[UploadFile, File(...)],
    dat: Annotated[UploadFile | None, File()] = None,
    manual_height_above_takeoff_m: Annotated[str | None, Form()] = None,
    manual_camera_angle_deg: Annotated[str | None, Form()] = None,
):
    """
    Persist video + telemetry.srt under a fresh flight id, parse, export sidecars.

    input: multipart video + srt; output: JSON envelope for UI bootstrap.
    """
    manual_meta = _parse_manual_metadata_form(manual_height_above_takeoff_m, manual_camera_angle_deg)

    storage = get_storage()
    flight_id = storage.new_flight_id()
    stored_video_name = derive_stored_video_name(video.filename or "")
    paths = storage.paths_for(flight_id, stored_video_name=stored_video_name)
    storage.ensure_layout(paths)

    vid_bytes = await video.read()
    srt_bytes = await srt.read()

    paths.video_path.write_bytes(vid_bytes)
    paths.srt_path.write_bytes(srt_bytes)

    dat_uploaded = False
    if dat is not None:
        dab = await dat.read()
        if dab:
            paths.dat_path.write_bytes(dab)
            dat_uploaded = True

    try:
        srt_text = srt_bytes.decode("utf-8")
    except UnicodeDecodeError:
        srt_text = srt_bytes.decode("latin-1", errors="replace")

    try:
        records = parse_dji_srt(srt_text)
    except SrtParseError as e:
        _invalidate_flight(paths.root)
        raise HTTPException(status_code=400, detail=str(e)) from e

    summary = build_summary(records)
    fields_detected = build_fields_detected(records)
    telemetry_json_obj = records_to_jsonable(records)

    vid_meta = extract_video_metadata(
        video_path=paths.video_path,
        original_filename=video.filename or paths.video_path.name,
        stored_filename=paths.video_path.name,
    )

    paths.telemetry_json.write_text(json.dumps(telemetry_json_obj, indent=2), encoding="utf-8")
    summary_dump = summary.model_dump()
    summary_dump["fields_detected"] = fields_detected
    paths.summary_json.write_text(json.dumps(summary_dump, indent=2), encoding="utf-8")
    paths.video_metadata_json.write_text(json.dumps(vid_meta.model_dump(), indent=2), encoding="utf-8")
    paths.flight_metadata_json.write_text(json.dumps(manual_meta.model_dump(), indent=2), encoding="utf-8")

    paths.export_csv.write_bytes(telemetry_to_csv_bytes(records))
    paths.export_kml.write_bytes(telemetry_to_kml_bytes(records, name=f"Flight {flight_id}"))

    return {
        "flight_id": flight_id,
        "video_url": f"/api/flights/{flight_id}/video",
        "records": telemetry_json_obj,
        "summary": summary_dump,
        "fields_detected": fields_detected,
        "video_metadata": vid_meta.model_dump(),
        "manual_metadata": manual_meta.model_dump(),
        "dat_uploaded": dat_uploaded,
    }


@router.get("/{flight_id}/video")
def stream_video(flight_id: str):
    storage = get_storage()
    if not _flight_dir_exists(storage, flight_id):
        raise HTTPException(status_code=404, detail="Flight not found.")

    raw_dir = storage.flights_root() / flight_id / "raw"
    vid_path = next(raw_dir.glob("video.*"), None)
    if not vid_path or not vid_path.is_file():
        raise HTTPException(status_code=404, detail="Video not found.")
    return video_file_response(vid_path)


@router.get("/{flight_id}/telemetry")
def get_telemetry(flight_id: str):
    storage = get_storage()
    processed = storage.flights_root() / flight_id / "processed"
    telemetry_path = processed / "telemetry.json"
    summary_path = processed / "summary.json"
    video_meta_path = processed / "video_metadata.json"
    if not telemetry_path.is_file():
        raise HTTPException(status_code=404, detail="Flight not found.")

    telemetry_data = json.loads(telemetry_path.read_text(encoding="utf-8"))
    summary_blob = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else {}
    video_blob = json.loads(video_meta_path.read_text(encoding="utf-8")) if video_meta_path.is_file() else {}

    validated_summary = FlightSummary(
        record_count=int(summary_blob.get("record_count", len(telemetry_data))),
        gps_point_count=int(summary_blob.get("gps_point_count", 0)),
        duration_seconds_srt_end=summary_blob.get("duration_seconds_srt_end"),
        home_lat=summary_blob.get("home_lat"),
        home_lon=summary_blob.get("home_lon"),
    )
    summary_public = validated_summary.model_dump()
    summary_public["fields_detected"] = summary_blob.get("fields_detected", [])

    return {
        "flight_id": flight_id,
        "records": telemetry_data,
        "summary": summary_public,
        "fields_detected": summary_blob.get("fields_detected", []),
        "video_metadata": video_blob,
    }


@router.get("/{flight_id}/exports/csv")
def export_csv(flight_id: str):
    path = _flight_export(get_storage(), flight_id, "telemetry.csv")
    return FileResponse(str(path), media_type="text/csv", filename=f"{flight_id}_telemetry.csv")


@router.get("/{flight_id}/exports/kml")
def export_kml_route(flight_id: str):
    path = _flight_export(get_storage(), flight_id, "path.kml")
    return FileResponse(
        str(path),
        media_type="application/vnd.google-earth.kml+xml",
        filename=f"{flight_id}_path.kml",
    )


@router.get("/{flight_id}/exports/json")
def export_json_file(flight_id: str):
    storage = get_storage()
    processed = storage.flights_root() / flight_id / "processed" / "telemetry.json"
    if not processed.is_file():
        raise HTTPException(status_code=404, detail="Flight telemetry not found.")
    return FileResponse(str(processed), media_type="application/json", filename=f"{flight_id}_telemetry.json")


def _flight_export(storage: FlightStorage, flight_id: str, name: str) -> Path:
    if not _flight_dir_exists(storage, flight_id):
        raise HTTPException(status_code=404, detail="Flight not found.")
    p = storage.flights_root() / flight_id / "exports" / name
    if not p.is_file():
        raise HTTPException(status_code=404, detail=f"Missing export file: {name}")
    return p
