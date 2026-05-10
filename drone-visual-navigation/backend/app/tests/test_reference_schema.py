"""Reference export schema."""

import pytest

from app.preprocessing.reference_schema import CSV_FIELD_ORDER, ReferenceFrameRecord


def test_reference_record_required_and_optional_none() -> None:
    row = ReferenceFrameRecord(
        reference_id="rid",
        frame_index=0,
        timestamp_seconds=0.0,
        image_path="frames/frame_000000.jpg",
        telemetry_block_index=None,
        drone_lat=None,
        drone_lon=None,
        rel_alt_m=None,
        abs_alt_m=None,
        manual_height_above_takeoff_m=None,
        manual_camera_angle_deg=None,
        local_x_m=None,
        local_y_m=None,
        feature_type="none",
        feature_path=None,
        feature_status="skipped",
    )
    d = row.model_dump()
    assert d["telemetry_block_index"] is None
    assert d["feature_type"] == "none"


def test_csv_field_order_stable() -> None:
    row = ReferenceFrameRecord(
        reference_id="r",
        frame_index=1,
        timestamp_seconds=1.5,
        image_path="f.jpg",
        feature_type="orb",
        feature_path="feat.npz",
        feature_status="extracted",
    )
    dumped = row.model_dump()
    assert CSV_FIELD_ORDER[0] == "reference_id"
    assert set(CSV_FIELD_ORDER) == set(dumped.keys())
    assert len(CSV_FIELD_ORDER) == len(dumped)


def test_negative_frame_index_rejected() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ReferenceFrameRecord(
            reference_id="r",
            frame_index=-1,
            timestamp_seconds=0.0,
            image_path="x",
            feature_type="none",
            feature_status="skipped",
        )
