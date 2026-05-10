"""Probe duration, frame size, and FPS from local video via ffprobe with OpenCV fallback."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

try:
    import cv2  # type: ignore
except ImportError:
    cv2 = None

from drone_nav.telemetry.telemetry_schema import VideoMetadataProbe


def _ffprobe(path: Path) -> dict | None:
    ff = shutil.which("ffprobe") or shutil.which("ffprobe.exe")
    if not ff:
        return None
    cmd = [
        ff,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not proc.stdout:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def extract_video_metadata(
    *,
    video_path: Path,
    original_filename: str,
    stored_filename: str,
) -> VideoMetadataProbe:
    """
    Probe video metadata from disk.

    input: absolute path plus original + stored basename for provenance labels.
    output: VideoMetadataProbe with probe_source tagging which backend succeeded.
    """

    pb = _ffprobe(video_path)
    if pb:
        width = height = None
        fps: float | None = None
        frame_count: int | None = None
        duration: float | None = None

        fmt = pb.get("format") or {}
        if "duration" in fmt:
            try:
                duration = float(fmt["duration"])
            except (TypeError, ValueError):
                duration = None

        for st in pb.get("streams") or []:
            if st.get("codec_type") != "video":
                continue
            try:
                width = int(st.get("width") or 0) or None
                height = int(st.get("height") or 0) or None
            except (TypeError, ValueError):
                width = height = None

            fr = st.get("avg_frame_rate") or st.get("r_frame_rate")
            if isinstance(fr, str) and "/" in fr:
                num, den = fr.split("/", 1)
                try:
                    n, d = float(num), float(den)
                    if d:
                        fps = n / d
                except ValueError:
                    fps = None
            if "nb_frames" in st and st["nb_frames"] not in (None, "N/A"):
                try:
                    frame_count = int(st["nb_frames"])
                except (TypeError, ValueError):
                    frame_count = None
            if duration is None and "duration" in st:
                try:
                    duration = float(st["duration"])
                except (TypeError, ValueError):
                    pass
            break

        if frame_count is None and duration is not None and fps:
            frame_count = int(round(duration * fps))

        return VideoMetadataProbe(
            fps=fps,
            frame_count=frame_count,
            duration_seconds=duration,
            width=width,
            height=height,
            original_filename=original_filename,
            stored_filename=stored_filename,
            probe_source="ffprobe",
        )

    if cv2 is None:
        return VideoMetadataProbe(
            fps=None,
            frame_count=None,
            duration_seconds=None,
            width=None,
            height=None,
            original_filename=original_filename,
            stored_filename=stored_filename,
            probe_source="none",
        )

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        cap.release()
        return VideoMetadataProbe(
            fps=None,
            frame_count=None,
            duration_seconds=None,
            width=None,
            height=None,
            original_filename=original_filename,
            stored_filename=stored_filename,
            probe_source="none",
        )

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or None
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or None
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0) or None
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) or None
    duration = None
    if fps and frame_count:
        duration = frame_count / fps
    cap.release()

    return VideoMetadataProbe(
        fps=fps,
        frame_count=frame_count,
        duration_seconds=duration,
        width=width,
        height=height,
        original_filename=original_filename,
        stored_filename=stored_filename,
        probe_source="opencv",
    )
