import type { FlightManualMetadata, FlightSession } from "../domain/flight";
import type { FlightSummary, TelemetryRecord, VideoMetadata } from "../domain/telemetry";

const API_BASE = import.meta.env.VITE_API_BASE?.replace(/\/$/, "") || "http://127.0.0.1:8000";

/** Base URL used for composing absolute media + download links. */
export function getApiBase(): string {
  return API_BASE;
}

interface UploadEnvelope {
  flight_id: string;
  video_url: string;
  records: TelemetryRecord[];
  summary: FlightSummary & { fields_detected?: string[] };
  fields_detected: string[];
  video_metadata: VideoMetadata;
  manual_metadata?: {
    manual_height_above_takeoff_m?: number | null;
    manual_camera_angle_deg?: number | null;
  };
  dat_uploaded?: boolean;
}

/**
 * Upload multipart video + SRT; returns normalized session envelope.
 *
 * input: browser File objects; output: `FlightSession` for UI bootstrap.
 */
/** Optional manual fields sent as multipart Form parts only when finite numbers are supplied. */
export async function uploadFlight(
  video: File,
  srt: File,
  manual?: Partial<FlightManualMetadata>,
  dat?: File,
): Promise<FlightSession> {
  const body = new FormData();
  body.append("video", video);
  body.append("srt", srt);
  if (dat) body.append("dat", dat);

  const h = manual?.manual_height_above_takeoff_m;
  if (typeof h === "number" && Number.isFinite(h)) {
    body.append("manual_height_above_takeoff_m", String(h));
  }
  const a = manual?.manual_camera_angle_deg;
  if (typeof a === "number" && Number.isFinite(a)) {
    body.append("manual_camera_angle_deg", String(a));
  }

  const resp = await fetch(`${API_BASE}/api/flights/upload`, {
    method: "POST",
    body,
  });

  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const data = await resp.json();
      if (typeof data?.detail === "string") {
        detail = data.detail;
      }
    } catch {
      /* ignore */
    }
    throw new Error(detail || "Upload failed");
  }

  const data = (await resp.json()) as UploadEnvelope;

  const summary = { ...data.summary };
  const mergedFields =
    data.fields_detected ?? summary.fields_detected ?? [];

  const mm = data.manual_metadata;
  const manualMetadata: FlightManualMetadata = {
    manual_height_above_takeoff_m:
      mm?.manual_height_above_takeoff_m != null &&
      typeof mm.manual_height_above_takeoff_m === "number" &&
      Number.isFinite(mm.manual_height_above_takeoff_m)
        ? mm.manual_height_above_takeoff_m
        : null,
    manual_camera_angle_deg:
      mm?.manual_camera_angle_deg != null &&
      typeof mm.manual_camera_angle_deg === "number" &&
      Number.isFinite(mm.manual_camera_angle_deg)
        ? mm.manual_camera_angle_deg
        : null,
  };

  return {
    flightId: data.flight_id,
    videoUrl: `${API_BASE}${data.video_url}`,
    records: data.records,
    summary: {
      ...summary,
      fields_detected: mergedFields,
    },
    fieldsDetected: mergedFields,
    videoMetadata: data.video_metadata,
    manualMetadata,
    datUploaded: Boolean(data.dat_uploaded),
  };
}

export function exportHref(flightId: string, kind: "csv" | "kml" | "json"): string {
  return `${API_BASE}/api/flights/${flightId}/exports/${kind}`;
}
