"""FastAPI integration surface; probe logic lives in ``drone_nav.preprocessing.video_metadata``."""

from drone_nav.preprocessing.video_metadata import extract_video_metadata

__all__ = ["extract_video_metadata"]
