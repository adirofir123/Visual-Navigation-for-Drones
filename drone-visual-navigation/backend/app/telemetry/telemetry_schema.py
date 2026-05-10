"""Pydantic models for DJI-format SRT-derived telemetry."""

from typing import Optional

from pydantic import BaseModel, Field


class TelemetryRecord(BaseModel):
    """One SRT cue’s parsed telemetry."""

    block_index: int = Field(description="Original SRT index line (may be synthesized if recovered).")
    start_time_raw: str
    end_time_raw: str
    start_time_seconds: float
    end_time_seconds: float
    raw_text: str

    home_lon: Optional[float] = None
    home_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    gps_lat: Optional[float] = None
    gps_alt: Optional[float] = None
    barometer: Optional[float] = None
    iso: Optional[float] = None
    shutter: Optional[float] = None
    ev: Optional[float] = None
    fnum: Optional[float] = None

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude_m: Optional[float] = None
    rel_altitude_m: Optional[float] = None
    rel_altitude: Optional[float] = None

    gimbal_pitch_deg: Optional[float] = None
    gimbal_roll_deg: Optional[float] = None
    gimbal_yaw_deg: Optional[float] = None
    yaw_deg: Optional[float] = None
    heading_deg: Optional[float] = None

    frame_count: Optional[int] = None
    diff_time_ms: Optional[float] = None
    capture_datetime: Optional[str] = None
    color_md: Optional[str] = None
    focal_len: Optional[float] = None
    ct: Optional[float] = None
    shutter_raw: Optional[str] = Field(
        default=None,
        description="Original shutter token (e.g. 1/8000 or 1/1000.0) when parsed from subtitles.",
    )


class FlightManualMetadata(BaseModel):
    """Optional user-supplied hints saved with each flight upload."""

    manual_height_above_takeoff_m: Optional[float] = None
    manual_camera_angle_deg: Optional[float] = None


class FlightSummary(BaseModel):
    """Aggregate stats computed after parsing all records."""

    record_count: int
    gps_point_count: int
    duration_seconds_srt_end: Optional[float] = Field(
        default=None,
        description="Latest end_time_seconds observed in SRT, if any.",
    )
    home_lat: Optional[float] = None
    home_lon: Optional[float] = None


class VideoMetadataProbe(BaseModel):
    """Technical metadata extracted from uploaded video."""

    fps: Optional[float] = None
    frame_count: Optional[int] = None
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    original_filename: str
    stored_filename: str
    probe_source: str = Field(description="'ffprobe' | 'opencv' | 'none'")
