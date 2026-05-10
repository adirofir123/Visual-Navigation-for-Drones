import { useMemo } from "react";

import type { TelemetryRecord } from "../domain/telemetry";
import type { PathPoint } from "../domain/mapTypes";
import { LeafletMapView } from "./LeafletMapView";

interface Props {
  records: TelemetryRecord[];
  /** Optional live location from synced cue. */
  currentRecord?: TelemetryRecord | null;
  className?: string;
}

function buildPath(records: TelemetryRecord[]): PathPoint[] {
  return records
    .filter(
      (r) =>
        typeof r.gps_lat === "number" &&
        typeof r.gps_lon === "number" &&
        Number.isFinite(r.gps_lat) &&
        Number.isFinite(r.gps_lon),
    )
    .map((r) => ({
      lat: r.gps_lat as number,
      lng: r.gps_lon as number,
      altitude: r.gps_alt,
    }));
}

function currentPoint(rec?: TelemetryRecord | null): PathPoint | null {
  if (!rec) return null;
  if (typeof rec.gps_lat !== "number" || typeof rec.gps_lon !== "number") {
    return null;
  }
  if (!Number.isFinite(rec.gps_lat) || !Number.isFinite(rec.gps_lon)) {
    return null;
  }
  return { lat: rec.gps_lat, lng: rec.gps_lon, altitude: rec.gps_alt ?? null };
}

/** Map wrapper translating telemetry records → abstract path primitives. */
export function DroneMap({ records, currentRecord, className }: Props) {
  const path = useMemo(() => buildPath(records), [records]);

  if (!path.length) {
    return (
      <div className={`map-empty map-empty--placeholder ${className ?? ""}`} role="status">
        <h3>No GPS path in this recording</h3>
        <p>
          No valid latitude/longitude pairs were found in the SRT cues, so there is nothing to plot on the map.
          Video and telemetry panels still work; try another telemetry file if you expected a track here.
        </p>
      </div>
    );
  }

  return (
    <LeafletMapView
      path={path}
      current={currentPoint(currentRecord)}
      className={className}
    />
  );
}
