#!/usr/bin/env python3
"""CLI: build reference dataset from MP4 + SRT (see app.preprocessing.reference_builder)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve()
_PROJECT_ROOT = _SCRIPT.parents[1]
_BACKEND_ROOT = _PROJECT_ROOT / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def main() -> int:
    from app.preprocessing.reference_builder import build_reference_dataset

    p = argparse.ArgumentParser(description="Prepare georeferenced reference frames from MP4 + SRT.")
    p.add_argument("--video", type=Path, required=True, help="Path to source MP4 (or video file).")
    p.add_argument("--srt", type=Path, required=True, help="Path to matching DJI SRT.")
    p.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Reference output directory (e.g. data/processed/flights/.../reference).",
    )
    p.add_argument(
        "--sample-every-seconds",
        type=float,
        default=1.0,
        help="Temporal stride between sampled frames (seconds).",
    )
    p.add_argument(
        "--manual-height-above-takeoff-m",
        type=float,
        default=None,
        help="Manual height above takeoff (meters), stored per row.",
    )
    p.add_argument(
        "--manual-camera-angle-deg",
        type=float,
        default=None,
        help="Manual camera angle (degrees), stored per row.",
    )
    p.add_argument(
        "--extract-orb-features",
        action="store_true",
        help="Compute OpenCV ORB features per frame into features/*.npz.",
    )

    ns = p.parse_args()
    if ns.sample_every_seconds <= 0:
        print("--sample-every-seconds must be positive.", file=sys.stderr)
        return 2

    try:
        paths = build_reference_dataset(
            video_path=ns.video,
            srt_path=ns.srt,
            output_reference_dir=ns.output,
            sample_every_seconds=float(ns.sample_every_seconds),
            manual_height_above_takeoff_m=ns.manual_height_above_takeoff_m,
            manual_camera_angle_deg=ns.manual_camera_angle_deg,
            extract_orb_features=bool(ns.extract_orb_features),
        )
        print(f"Reference dataset written under: {paths.reference_root}")
        print(f"  {paths.reference_frames_json.name}")
        print(f"  {paths.reference_frames_csv.name}")
        print(f"  {paths.reference_summary_json.name}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
