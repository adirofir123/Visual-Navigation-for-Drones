import L from "leaflet";
import { useEffect, useMemo } from "react";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Polyline,
  TileLayer,
  Tooltip,
  useMap,
} from "react-leaflet";

import type { FlightMapProps } from "../domain/mapTypes";

type LatTuple = [number, number];

/** Re-sync Leaflet sizing when container dimensions change (grid/flex). */
function InvalidateOnResize() {
  const map = useMap();

  useEffect(() => {
    const el = map.getContainer();
    const run = () => {
      requestAnimationFrame(() => {
        map.invalidateSize({ animate: false });
      });
    };
    run();
    const ro = new ResizeObserver(run);
    ro.observe(el);
    return () => ro.disconnect();
  }, [map]);

  return null;
}

function FitWatcher({ bounds }: { bounds: L.LatLngBounds | null }) {
  const map = useMap();

  useEffect(() => {
    requestAnimationFrame(() => {
      map.invalidateSize({ animate: false });
      if (bounds?.isValid()) {
        map.fitBounds(bounds, { padding: [36, 36], maxZoom: 18 });
      }
    });
  }, [bounds, map]);

  return null;
}

function useDroneMarkerIcon(): L.DivIcon {
  return useMemo(
    () =>
      L.divIcon({
        className: "drone-pos-marker",
        html: '<div class="drone-pos-marker-inner" aria-hidden="true">🚁</div>',
        iconSize: [36, 36],
        iconAnchor: [18, 18],
        tooltipAnchor: [0, -16],
      }),
    [],
  );
}

/**
 * Concrete Leaflet + OSM visualization for sampled GPS path + live marker.
 *
 * Future work: sibling `GoogleMapView` swapping tile + overlay layers only.
 */
export function LeafletMapView({ path, current, className }: FlightMapProps) {
  const droneIcon = useDroneMarkerIcon();
  const polyline = useMemo(() => path.map((p) => [p.lat, p.lng] as LatTuple), [path]);
  const bounds = useMemo(() => {
    if (polyline.length > 1) {
      return L.latLngBounds(polyline.map(([lat, lng]) => [lat, lng]));
    }
    if (polyline.length === 1) {
      return L.latLngBounds(polyline[0], polyline[0]);
    }
    return null;
  }, [polyline]);

  const center: LatTuple = polyline[0]
    ? polyline[0]
    : current
      ? [current.lat, current.lng]
      : [51.505, -0.09];

  return (
    <div className={`map-frame ${className ?? ""}`}>
      <MapContainer
        className="map-surface"
        center={center}
        zoom={16}
        scrollWheelZoom
        style={{ width: "100%" }}
      >
        <InvalidateOnResize />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitWatcher bounds={bounds} />
        {polyline.length > 1 ? (
          <Polyline positions={polyline} pathOptions={{ color: "#2563eb", weight: 4, opacity: 0.95 }} />
        ) : polyline.length === 1 ? (
          <CircleMarker center={polyline[0]} radius={5} pathOptions={{ color: "#2563eb", fillOpacity: 0.5 }} />
        ) : null}
        {polyline.length ? (
          <CircleMarker center={polyline[0]} radius={6} pathOptions={{ color: "#10b981", fillOpacity: 0.95 }}>
            <Tooltip direction="top" opacity={1}>
              Start
            </Tooltip>
          </CircleMarker>
        ) : null}
        {polyline.length > 1 ? (
          <CircleMarker center={polyline[polyline.length - 1]} radius={6} pathOptions={{ color: "#ef4444", fillOpacity: 0.95 }}>
            <Tooltip direction="top" opacity={1}>
              End
            </Tooltip>
          </CircleMarker>
        ) : null}
        {current ? (
          <Marker position={[current.lat, current.lng]} icon={droneIcon}>
            <Tooltip direction="top" opacity={0.95} offset={[0, -8]}>
              Current ({current.lat.toFixed(5)}, {current.lng.toFixed(5)})
            </Tooltip>
          </Marker>
        ) : null}
      </MapContainer>
    </div>
  );
}
