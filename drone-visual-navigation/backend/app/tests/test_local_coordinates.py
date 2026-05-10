"""Local tangent plane lat/lon conversions."""

import pytest

from drone_nav.geometry.local_coordinates import LocalTangentOrigin, first_origin_from_records, usable_pair_lat_lon
from drone_nav.telemetry.telemetry_schema import TelemetryRecord


def test_usable_pair_prefers_gps_fields() -> None:
    assert usable_pair_lat_lon(10.0, 20.0, 30.0, 40.0) == (10.0, 20.0)


def test_first_origin_from_records() -> None:
    r_bad = TelemetryRecord(
        block_index=1,
        start_time_raw="00:00:00,000 --> 00:00:00,010",
        end_time_raw="00:00:00,000 --> 00:00:00,010",
        start_time_seconds=0.0,
        end_time_seconds=0.01,
        raw_text="",
    )
    r_ok = r_bad.model_copy(
        update=dict(
            block_index=2,
            gps_lat=32.102,
            gps_lon=35.209,
        ),
    )
    o = first_origin_from_records([r_bad, r_ok])
    assert o is not None
    assert o[0] == pytest.approx(32.102)
    assert o[1] == pytest.approx(35.209)


def test_xy_round_trip_approximate() -> None:
    origin = LocalTangentOrigin(lat0_deg=32.1, lon0_deg=35.2)
    lat, lon = 32.1005, 35.2003
    x, y = origin.to_local_xy(lat, lon)
    lat_b, lon_b = origin.approx_lat_lon_from_xy(x, y)
    assert lat_b == pytest.approx(lat, abs=1e-10)
    assert lon_b == pytest.approx(lon, abs=1e-10)
