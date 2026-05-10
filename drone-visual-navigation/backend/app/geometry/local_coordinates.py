"""
Local tangent-plane XY in meters relative to an origin latitude/longitude.

Uses a compact equirectangular-style linearization on the WGS84 authalic sphere
.radius (~ drone-scale accuracy). Error grows with distance from the origin; do
not use for global surveying.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.telemetry.telemetry_schema import TelemetryRecord

_WGS84_AUTHALIC_RADIUS_M = 6371007.0


def _finite(v: float | None) -> bool:
    return v is not None and math.isfinite(v)


def usable_pair_lat_lon(
    gps_lat: float | None,
    gps_lon: float | None,
    lat: float | None,
    lon: float | None,
) -> tuple[float, float] | None:
    """Prefer gps_*; fallback to latitude/longitude; reject implausible magnitudes."""

    plat = gps_lat if _finite(gps_lat) else None
    plon = gps_lon if _finite(gps_lon) else None
    if plat is None and _finite(lat):
        plat = lat
    if plon is None and _finite(lon):
        plon = lon
    if plat is None or plon is None:
        return None
    if abs(plat) > 90.0 or abs(plon) > 180.0:
        return None
    return float(plat), float(plon)


def first_origin_from_records(records: list[TelemetryRecord]) -> tuple[float, float] | None:
    """First cues with usable lat/lon (gps fields preferred over bracket lat/lon)."""

    for r in records:
        pair = usable_pair_lat_lon(r.gps_lat, r.gps_lon, r.latitude, r.longitude)
        if pair:
            return pair
    return None


@dataclass(frozen=True)
class LocalTangentOrigin:
    lat0_deg: float
    lon0_deg: float

    def to_local_xy(self, lat_deg: float, lon_deg: float) -> tuple[float, float]:
        lon_scale = math.cos(math.radians(self.lat0_deg))
        dx_m = _WGS84_AUTHALIC_RADIUS_M * math.radians(lon_deg - self.lon0_deg) * lon_scale
        dy_m = _WGS84_AUTHALIC_RADIUS_M * math.radians(lat_deg - self.lat0_deg)
        return dx_m, dy_m

    def approx_lat_lon_from_xy(self, x_m: float, y_m: float) -> tuple[float, float]:
        """Inverse of to_local_xy for the same linearization (approximate)."""

        lat = self.lat0_deg + math.degrees(y_m / _WGS84_AUTHALIC_RADIUS_M)
        lon_scale = math.cos(math.radians(self.lat0_deg))
        if lon_scale == 0.0:
            lon = self.lon0_deg
        else:
            lon = self.lon0_deg + math.degrees(x_m / (_WGS84_AUTHALIC_RADIUS_M * lon_scale))
        return lat, lon

    @classmethod
    def from_first_gps_records(cls, records: list[TelemetryRecord]) -> LocalTangentOrigin | None:
        o = first_origin_from_records(records)
        if o is None:
            return None
        return cls(lat0_deg=o[0], lon0_deg=o[1])
