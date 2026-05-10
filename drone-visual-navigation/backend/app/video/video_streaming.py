"""
Serve stored video files for HTML5 playback.

TODO: If seeking is unreliable in some browsers, implement explicit HTTP Range
handling (Content-Range / 206 / 416) or verify Starlette FileResponse behavior
for your target browsers and codecs.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from starlette.responses import FileResponse


def guess_video_media_type(path: Path) -> str:
    """Map file extension to MIME type; default to video/mp4."""

    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "video/mp4"


def video_file_response(video_path: Path) -> FileResponse:
    """input: validated path to flight video file; output: FileResponse streaming body."""

    return FileResponse(
        path=str(video_path),
        media_type=guess_video_media_type(video_path),
        filename=video_path.name,
        content_disposition_type="inline",
    )
