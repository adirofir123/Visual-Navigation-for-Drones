"""
Build georeferenced reference frames from DJI MP4 + SRT (offline / CLI).

Seeks decoded frames via OpenCV; accuracy depends on GOP keyframes — acceptable
for reference sampling at coarse intervals.

input: Paths + sampling stride + optional manual metadata + ORB flag.
output: ``frames/*.jpg``, optional ``features/*_orb.npz``, manifests JSON/CSV.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

try:
    import cv2  # type: ignore
except ImportError:
    cv2 = None

from drone_nav.geometry.local_coordinates import LocalTangentOrigin, usable_pair_lat_lon
from drone_nav.preprocessing.frame_sampler import NearestCueIndex, frame_index_at_time, samples_seconds
from drone_nav.preprocessing.reference_schema import (
    ReferenceDatasetSummary,
    ReferenceFrameRecord,
    telemetry_to_drone_geo,
    write_reference_frames_csv,
    write_reference_frames_json,
    write_reference_summary_json,
)
from drone_nav.telemetry.telemetry_schema import TelemetryRecord
from drone_nav.telemetry.srt_parser import SrtParseError, parse_dji_srt
from drone_nav.preprocessing.video_metadata import extract_video_metadata


def _decode_srt_text(path: Path) -> str:
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", errors="replace")


JPEG_QUALITY = 95


def _rel_posix(reference_root: Path, target: Path) -> str:
    return target.relative_to(reference_root).as_posix()


@dataclass(frozen=True)
class BuiltReferencePaths:
    reference_root: Path
    frames_dir: Path
    features_dir: Path
    reference_frames_json: Path
    reference_frames_csv: Path
    reference_summary_json: Path


def build_reference_dataset(
    *,
    video_path: Path,
    srt_path: Path,
    output_reference_dir: Path,
    sample_every_seconds: float,
    manual_height_above_takeoff_m: float | None = None,
    manual_camera_angle_deg: float | None = None,
    extract_orb_features: bool = False,
    reference_id: str | None = None,
) -> BuiltReferencePaths:
    if cv2 is None:
        raise RuntimeError("OpenCV is required for reference extraction (opencv-python-headless).")

    video_path = video_path.resolve()
    srt_path = srt_path.resolve()
    ref_root = output_reference_dir.resolve()
    frames_dir = ref_root / "frames"
    features_dir = ref_root / "features"
    frames_dir.mkdir(parents=True, exist_ok=True)
    features_dir.mkdir(parents=True, exist_ok=True)

    ref_id = reference_id or str(uuid.uuid4())

    try:
        records = parse_dji_srt(_decode_srt_text(srt_path))
    except SrtParseError as e:
        raise RuntimeError(str(e)) from e

    vid_meta = extract_video_metadata(
        video_path=video_path,
        original_filename=video_path.name,
        stored_filename=video_path.name,
    )
    fps = vid_meta.fps
    duration = vid_meta.duration_seconds
    frame_cnt = vid_meta.frame_count

    if fps is None or fps <= 0 or not math.isfinite(fps):
        raise RuntimeError("Video FPS unavailable or invalid — install ffprobe or ensure OpenCV can read FPS.")

    if duration is None or duration <= 0:
        cap_probe = cv2.VideoCapture(str(video_path))
        if cap_probe.isOpened() and fps:
            n = cap_probe.get(cv2.CAP_PROP_FRAME_COUNT)
            cap_probe.release()
            try:
                n_int = int(n)
                if n_int > 0:
                    duration = float(n_int) / fps
                    frame_cnt = frame_cnt or n_int
            except (TypeError, ValueError):
                pass
    if duration is None or duration <= 0:
        raise RuntimeError("Video duration could not be determined.")

    indexer = NearestCueIndex.from_records(records)
    by_block: dict[int, TelemetryRecord] = {r.block_index: r for r in records}

    origin = LocalTangentOrigin.from_first_gps_records(records)
    origin_lat = origin.lat0_deg if origin else None
    origin_lon = origin.lon0_deg if origin else None

    sample_times = samples_seconds(duration_s=duration, stride_s=sample_every_seconds)
    if not sample_times:
        sample_times = [0.0]

    orb_extract_fn = None
    if extract_orb_features:
        from drone_nav.features.orb_features import extract_orb_to_npz

        orb_extract_fn = extract_orb_to_npz

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {video_path}")

    rows: list[ReferenceFrameRecord] = []
    orb_written = 0
    orb_counts: list[int] = []
    gps_rows = 0
    nogps_rows = 0

    for t in sample_times:
        fidx = frame_index_at_time(t, fps, frame_count=frame_cnt)
        cap.set(cv2.CAP_PROP_POS_FRAMES, float(fidx))
        ok, bgr = cap.read()
        if not ok or bgr is None or bgr.size == 0:
            cap.release()
            raise RuntimeError(f"Failed to read frame_index={fidx} at timestamp_s≈{t}")

        fname = f"frame_{fidx:06d}.jpg"
        img_path_disk = frames_dir / fname
        cv2.imwrite(
            str(img_path_disk),
            bgr,
            [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY],
        )

        rec = indexer.nearest_record(t, by_block)
        telemetry_block_idx = rec.block_index if rec else None
        dlat: float | None = None
        dlon: float | None = None
        rel_m: float | None = None
        abs_m: float | None = None
        lx: float | None = None
        ly: float | None = None
        if rec is None:
            nogps_rows += 1
        else:
            dlat, dlon, rel_m, abs_m = telemetry_to_drone_geo(rec)
            pair = usable_pair_lat_lon(rec.gps_lat, rec.gps_lon, rec.latitude, rec.longitude)
            if pair and origin:
                lx, ly = origin.to_local_xy(pair[0], pair[1])
            if pair:
                gps_rows += 1
            else:
                nogps_rows += 1

        feat_type = "orb" if extract_orb_features else "none"
        feat_rel: str | None = None
        feat_status = "skipped"
        nkp = 0
        if extract_orb_features and orb_extract_fn is not None:
            nz_name = f"frame_{fidx:06d}_orb.npz"
            nz_path = features_dir / nz_name
            nkp = orb_extract_fn(bgr, nz_path)
            feat_rel = _rel_posix(ref_root, nz_path)
            feat_status = "extracted"
            orb_written += 1
            orb_counts.append(nkp)
        elif extract_orb_features:
            feat_status = "failed"

        rows.append(
            ReferenceFrameRecord(
                reference_id=ref_id,
                frame_index=fidx,
                timestamp_seconds=float(t),
                image_path=_rel_posix(ref_root, img_path_disk),
                telemetry_block_index=telemetry_block_idx,
                drone_lat=dlat,
                drone_lon=dlon,
                rel_alt_m=rel_m,
                abs_alt_m=abs_m,
                manual_height_above_takeoff_m=manual_height_above_takeoff_m,
                manual_camera_angle_deg=manual_camera_angle_deg,
                local_x_m=lx,
                local_y_m=ly,
                feature_type=feat_type,
                feature_path=feat_rel,
                feature_status=feat_status,
            ),
        )

    cap.release()

    pj = ref_root / "reference_frames.json"
    pc = ref_root / "reference_frames.csv"
    ps = ref_root / "reference_summary.json"

    write_reference_frames_json(pj, rows)
    write_reference_frames_csv(pc, rows)

    summary = ReferenceDatasetSummary(
        reference_id=ref_id,
        generated_at_iso=datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        video_path=str(video_path),
        srt_path=str(srt_path),
        output_dir=str(ref_root),
        fps=fps,
        frame_count=frame_cnt,
        duration_seconds=duration,
        video_probe_source=vid_meta.probe_source,
        stride_seconds=float(sample_every_seconds),
        sample_count=len(rows),
        origin_lat_deg=origin_lat,
        origin_lon_deg=origin_lon,
        rows_with_gps=gps_rows,
        rows_missing_gps=nogps_rows,
        extract_orb=extract_orb_features,
        orb_frames_written=orb_written,
        orb_keypoint_counts=orb_counts,
    )
    write_reference_summary_json(ps, summary)

    return BuiltReferencePaths(
        reference_root=ref_root,
        frames_dir=frames_dir,
        features_dir=features_dir,
        reference_frames_json=pj,
        reference_frames_csv=pc,
        reference_summary_json=ps,
    )
