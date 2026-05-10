"""KML export geometry tests."""

from app.geo.kml_exporter import telemetry_to_kml_bytes
from app.telemetry.telemetry_schema import TelemetryRecord


def _rec(lon: float, lat: float, alt: float | None) -> TelemetryRecord:
    return TelemetryRecord(
        block_index=1,
        start_time_raw="00:00:00,000",
        end_time_raw="00:00:01,000",
        start_time_seconds=0.0,
        end_time_seconds=1.0,
        raw_text=f"GPS({lon},{lat},{alt})",
        gps_lon=lon,
        gps_lat=lat,
        gps_alt=alt,
    )


def test_kml_linestring_coordinate_order() -> None:
    recs = [
        _rec(149.02, -20.25, 10.5),
        _rec(149.03, -20.26, 11.5),
        _rec(149.04, -20.27, 12.5),
    ]
    kml = telemetry_to_kml_bytes(recs).decode("utf-8")
    assert "149.02,-20.25,10.5" in kml.replace(" ", "")
    assert "-20.25,149.02" not in kml.replace(" ", "")


def test_kml_skips_invalid_gps() -> None:
    bad = TelemetryRecord(
        block_index=1,
        start_time_raw="00:00:00,000",
        end_time_raw="00:00:01,000",
        start_time_seconds=0.0,
        end_time_seconds=1.0,
        raw_text="no gps",
        gps_lon=None,
        gps_lat=None,
    )
    kml = telemetry_to_kml_bytes([bad]).decode("utf-8")
    assert "LineString" not in kml
