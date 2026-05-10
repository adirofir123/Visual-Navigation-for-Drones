/**
 * Client-side telemetry record shape mirrored from backend `TelemetryRecord`.
 *
 * Keeps parity with REST JSON (`null` for missing values).
 */

export interface TelemetryRecord {
  block_index: number;
  start_time_raw: string;
  end_time_raw: string;
  start_time_seconds: number;
  end_time_seconds: number;
  raw_text: string;
  home_lon?: number | null;
  home_lat?: number | null;
  gps_lon?: number | null;
  gps_lat?: number | null;
  gps_alt?: number | null;
  barometer?: number | null;
  iso?: number | null;
  shutter?: number | null;
  ev?: number | null;
  fnum?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  altitude_m?: number | null;
  rel_altitude_m?: number | null;
  rel_altitude?: number | null;
  gimbal_pitch_deg?: number | null;
  gimbal_roll_deg?: number | null;
  gimbal_yaw_deg?: number | null;
  yaw_deg?: number | null;
  heading_deg?: number | null;
  frame_count?: number | null;
  diff_time_ms?: number | null;
  capture_datetime?: string | null;
  color_md?: string | null;
  focal_len?: number | null;
  ct?: number | null;
  shutter_raw?: string | null;
}

export interface FlightSummary {
  record_count: number;
  gps_point_count: number;
  duration_seconds_srt_end?: number | null;
  home_lat?: number | null;
  home_lon?: number | null;
  fields_detected?: string[];
}

export interface VideoMetadata {
  fps?: number | null;
  frame_count?: number | null;
  duration_seconds?: number | null;
  width?: number | null;
  height?: number | null;
  original_filename: string;
  stored_filename: string;
  probe_source: string;
}
