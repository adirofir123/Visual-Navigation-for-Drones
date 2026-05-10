import type { TelemetryRecord } from "./telemetry";

export interface SyncMatch {
  record: TelemetryRecord;
  /** Signed distance in seconds from video time to cue midpoint. */
  deltaSeconds: number;
}

/**
 * Map current video time to the closest SRT cue using midpoint matching.
 *
 * input: ordered telemetry records, current wall clock of the video in seconds, optional max gap.
 * output: matched record + delta, or null if no sufficiently close cue exists.
 */
export function findTelemetryForTime(
  records: TelemetryRecord[],
  currentTimeSeconds: number,
  maxGapSeconds = 2.5,
): SyncMatch | null {
  if (!records.length) {
    return null;
  }

  let best: TelemetryRecord | null = null;
  let bestAbs = Number.POSITIVE_INFINITY;
  let bestDelta = 0;

  for (const r of records) {
    const mid = (r.start_time_seconds + r.end_time_seconds) / 2;
    const delta = currentTimeSeconds - mid;
    const dist = Math.abs(delta);
    if (dist < bestAbs) {
      bestAbs = dist;
      best = r;
      bestDelta = delta;
    }
  }

  if (!best || bestAbs > maxGapSeconds) {
    return null;
  }

  return { record: best, deltaSeconds: bestDelta };
}
