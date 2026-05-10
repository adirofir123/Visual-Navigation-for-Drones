/**
 * Minimal map primitives so Leaflet/Google implementations can swap later.
 */

export interface PathPoint {
  lat: number;
  lng: number;
  altitude?: number | null;
}

export interface FlightMapProps {
  path: PathPoint[];
  /** Current synced drone position — omitted when unknown. */
  current?: PathPoint | null;
  className?: string;
}
