import type { FlightSummary, TelemetryRecord, VideoMetadata } from "./telemetry";

/** Optional hints entered in the Load flight modal (stored server-side per flight). */
export interface FlightManualMetadata {
  manual_height_above_takeoff_m: number | null;
  manual_camera_angle_deg: number | null;
}

/** Active session after successful upload or reload. */
export interface FlightSession {
  flightId: string;
  videoUrl: string;
  records: TelemetryRecord[];
  summary: FlightSummary;
  fieldsDetected: string[];
  videoMetadata: VideoMetadata;
  manualMetadata: FlightManualMetadata;
  /** Optional DJI flight log stored server-side for future tooling (not parsed in-app). */
  datUploaded?: boolean;
}
