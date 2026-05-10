"""Telemetry SRT parsing unit tests."""

import pytest

from drone_nav.telemetry.srt_parser import SrtParseError, parse_timestamp_to_seconds, parse_dji_srt


def test_timestamp_to_seconds() -> None:
    assert pytest.approx(parse_timestamp_to_seconds("00:00:01,000")) == 1.0
    assert pytest.approx(parse_timestamp_to_seconds("01:02:03,456")) == 3723.456


SAMPLE_BLOCK = """1
00:00:01,000 --> 00:00:02,000
HOME(149.0251,-20.2532) 2017.08.05 14:11:51
GPS(149.0251,-20.2533,16) BAROMETER:1.9
ISO:100 Shutter:60 EV: Fnum:2.2
"""


def test_parse_sample_block_gps_lon_lat_order() -> None:
    records = parse_dji_srt(SAMPLE_BLOCK + "\n\n")
    assert len(records) == 1
    r = records[0]
    assert r.block_index == 1
    assert r.gps_lon == pytest.approx(149.0251)
    assert r.gps_lat == pytest.approx(-20.2533)
    assert r.gps_alt == pytest.approx(16)
    assert r.home_lon == pytest.approx(149.0251)
    assert r.home_lat == pytest.approx(-20.2532)
    assert r.barometer == pytest.approx(1.9)
    assert r.iso == pytest.approx(100)
    assert r.shutter == pytest.approx(60)
    assert r.fnum == pytest.approx(2.2)


def test_malformed_file_raises_typed_error() -> None:
    with pytest.raises(SrtParseError):
        parse_dji_srt("not a subtitle")


def test_tolerance_extra_blank_between_cues() -> None:
    second = """2
00:00:02,000 --> 00:00:03,000
GPS(149.0,-20.1,9)
"""
    text = SAMPLE_BLOCK + "\n\n\n\n" + second
    records = parse_dji_srt(text)
    assert len(records) == 2


BRACKET_SAMPLE = '''1
00:00:01,000 --> 00:00:02,000
<font size="28">FrameCnt: 1, DiffTime: 33ms
2026-04-27 15:22:26.853
[iso: 100] [shutter: 1/1000.0] [fnum: 1.7] [ev: 0] [color_md: default] [focal_len: 24.00] [latitude: 32.102624] [longitude: 35.209724] [rel_alt: 19.600 abs_alt: 729.642] [ct: 5660] </font>
'''


def test_parse_bracket_dji_sample() -> None:
    records = parse_dji_srt(BRACKET_SAMPLE + "\n")
    assert len(records) == 1
    r = records[0]
    assert r.frame_count == 1
    assert r.diff_time_ms == pytest.approx(33.0)
    assert r.capture_datetime == "2026-04-27 15:22:26.853"
    assert r.iso == pytest.approx(100)
    assert r.shutter_raw == "1/1000.0"
    assert r.shutter == pytest.approx(0.001)
    assert r.fnum == pytest.approx(1.7)
    assert r.ev == pytest.approx(0.0)
    assert r.color_md == "default"
    assert r.focal_len == pytest.approx(24.0)
    assert r.ct == pytest.approx(5660.0)
    assert r.gps_lat == pytest.approx(32.102624)
    assert r.gps_lon == pytest.approx(35.209724)
    assert r.rel_altitude == pytest.approx(19.6)
    assert r.altitude_m == pytest.approx(729.642)
    assert r.gps_alt == pytest.approx(729.642)
