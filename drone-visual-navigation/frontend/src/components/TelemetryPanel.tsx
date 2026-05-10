import type { FlightSession } from "../domain/flight";
import type { SyncMatch } from "../domain/sync";
import type { TelemetryRecord } from "../domain/telemetry";
import { formatClock } from "../utils/formatTime";
import { FlightSummaryCard } from "./FlightSummaryCard";
import { TimelineSyncDebug } from "./TimelineSyncDebug";

interface Props {
  session: FlightSession;
  currentSeconds: number;
  record?: TelemetryRecord | null;
  syncMatch?: SyncMatch | null;
}

function fmtNum(v?: number | null, digits = 4): string {
  return typeof v === "number" && Number.isFinite(v) ? v.toFixed(digits) : "N/A";
}

function fmtText(v?: string | null): string {
  return v != null && String(v).trim() !== "" ? String(v).trim() : "N/A";
}

function fmtShutter(record?: TelemetryRecord | null): string {
  if (!record) return "N/A";
  if (record.shutter_raw != null && String(record.shutter_raw).trim() !== "") {
    return String(record.shutter_raw).trim();
  }
  return fmtNum(record.shutter);
}

/** Gimbal degrees: distinguish “no synced cue” from “cue missing this field”. */
function fmtGimbalSrtDegrees(record: TelemetryRecord | undefined | null, deg?: number | null): string {
  if (!record) return "N/A";
  if (typeof deg === "number" && Number.isFinite(deg)) return deg.toFixed(2);
  return "Not present in SRT";
}

/** Prefer yaw_deg, else heading_deg; “Not present in SRT” when both missing on a synced cue. */
function fmtYawHeadingSrt(record: TelemetryRecord | undefined | null): string {
  if (!record) return "N/A";
  const { yaw_deg: y, heading_deg: h } = record;
  if (typeof y === "number" && Number.isFinite(y)) return y.toFixed(2);
  if (typeof h === "number" && Number.isFinite(h)) return h.toFixed(2);
  return "Not present in SRT";
}

/** Primary inspector: mission summary, timeline, parsed fields, collapsible raw cue. */
export function TelemetryPanel({ session, currentSeconds, record, syncMatch }: Props) {
  return (
    <div className="telemetry-panel">
      <div className="telemetry-scroll">
        {session.datUploaded ? (
          <p className="muted flight-meta-sub" role="status" style={{ margin: "0 0 10px" }}>
            DAT uploaded for future telemetry investigation.
          </p>
        ) : null}
        <div className="panel-section telemetry-flight-summary">
          <h3>Flight summary</h3>
          <FlightSummaryCard session={session} />
        </div>

        <div className="panel-section panel-section-compact">
          <h3>Manual metadata</h3>
          {session.manualMetadata.manual_height_above_takeoff_m == null &&
          session.manualMetadata.manual_camera_angle_deg == null ? (
            <p className="muted flight-meta-sub" style={{ margin: 0 }}>
              No manual metadata provided.
            </p>
          ) : (
            <dl className="kv-grid kv-grid-wide">
              <dt>Height above takeoff</dt>
              <dd>
                {session.manualMetadata.manual_height_above_takeoff_m != null
                  ? `${session.manualMetadata.manual_height_above_takeoff_m.toFixed(2)} m`
                  : "—"}
              </dd>
              <dt>Camera angle</dt>
              <dd>
                {session.manualMetadata.manual_camera_angle_deg != null
                  ? `${session.manualMetadata.manual_camera_angle_deg.toFixed(1)}°`
                  : "—"}
              </dd>
            </dl>
          )}
        </div>

        <div className="panel-section">
          <div className="panel-title-row">
            <h3>Timeline</h3>
            <span className="chip chip-neutral">{formatClock(currentSeconds)}</span>
          </div>
          <dl className="kv-grid kv-grid-wide">
            <dt>SRT cue</dt>
            <dd>{record ? `#${record.block_index}` : "No synced telemetry"}</dd>
            <dt>SRT span</dt>
            <dd>{record ? `${record.start_time_raw} → ${record.end_time_raw}` : "N/A"}</dd>
          </dl>
        </div>

        <div className="panel-section">
          <h3>Cue metadata (DJI)</h3>
          <dl className="kv-grid kv-grid-wide">
            <dt>Frame count</dt>
            <dd>{record?.frame_count != null ? String(record.frame_count) : "N/A"}</dd>
            <dt>Diff time</dt>
            <dd>{record?.diff_time_ms != null ? `${fmtNum(record.diff_time_ms, 0)} ms` : "N/A"}</dd>
            <dt>Capture datetime</dt>
            <dd className="kv-wrap">{fmtText(record?.capture_datetime)}</dd>
          </dl>
        </div>

        <div className="panel-section">
          <h3>Position and altitude</h3>
          <dl className="kv-grid kv-grid-wide">
            <dt>GPS latitude</dt>
            <dd>{fmtNum(record?.gps_lat)}</dd>
            <dt>GPS longitude</dt>
            <dd>{fmtNum(record?.gps_lon)}</dd>
            <dt>GPS altitude</dt>
            <dd>{fmtNum(record?.gps_alt, 2)}</dd>
            <dt>Relative altitude</dt>
            <dd>{fmtNum(record?.rel_altitude ?? record?.rel_altitude_m, 2)}</dd>
            <dt>Absolute altitude</dt>
            <dd>{fmtNum(record?.altitude_m, 2)}</dd>
            <dt>Barometer</dt>
            <dd>{fmtNum(record?.barometer, 3)}</dd>
            <dt>Home latitude</dt>
            <dd>{fmtNum(record?.home_lat)}</dd>
            <dt>Home longitude</dt>
            <dd>{fmtNum(record?.home_lon)}</dd>
          </dl>
        </div>

        <div className="panel-section">
          <h3>Exposure and optics</h3>
          <dl className="kv-grid kv-grid-wide">
            <dt>ISO</dt>
            <dd>{fmtNum(record?.iso)}</dd>
            <dt>Shutter</dt>
            <dd>{fmtShutter(record)}</dd>
            <dt>Shutter (numeric)</dt>
            <dd>{fmtNum(record?.shutter, 6)}</dd>
            <dt>EV</dt>
            <dd>{fmtNum(record?.ev, 3)}</dd>
            <dt>F-number</dt>
            <dd>{fmtNum(record?.fnum, 3)}</dd>
            <dt>Focal length</dt>
            <dd>{fmtNum(record?.focal_len, 2)}</dd>
            <dt>Color mode</dt>
            <dd>{fmtText(record?.color_md)}</dd>
            <dt>CT</dt>
            <dd>{fmtNum(record?.ct, 1)}</dd>
          </dl>
        </div>

        <div className="panel-section">
          <h3>Gimbal and heading</h3>
          <dl className="kv-grid kv-grid-wide">
            <dt>Gimbal pitch</dt>
            <dd>{fmtGimbalSrtDegrees(record, record?.gimbal_pitch_deg)}</dd>
            <dt>Gimbal roll</dt>
            <dd>{fmtGimbalSrtDegrees(record, record?.gimbal_roll_deg)}</dd>
            <dt>Gimbal yaw</dt>
            <dd>{fmtGimbalSrtDegrees(record, record?.gimbal_yaw_deg)}</dd>
            <dt>Yaw / heading</dt>
            <dd>{fmtYawHeadingSrt(record ?? null)}</dd>
          </dl>
        </div>
      </div>

      <details className="debug-details">
        <summary>Raw SRT cue and sync debug</summary>
        <div className="debug-inner">
          <TimelineSyncDebug match={syncMatch ?? null} />
          <pre className="raw-snippet">{record?.raw_text ?? "No synced telemetry cue."}</pre>
        </div>
      </details>
    </div>
  );
}
