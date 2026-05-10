"""
Parse DJI-style SRT subtitles into structured telemetry records.

Input: UTF-8 (or latin-1 fallback from caller) subtitle text conforming loosely to standard SRT.
Output: typed TelemetryRecord list + summary helpers.
"""

from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from drone_nav.telemetry.telemetry_schema import FlightSummary, TelemetryRecord


class SrtParseError(Exception):
    """Raised when the file cannot yield any valid cues (UI/API should surface `.args[0]`)."""


_TIMESTAMP_LINE = re.compile(
    r"^\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*$"
)


def parse_timestamp_to_seconds(ts: str) -> float:
    """Convert HH:MM:SS,mmm or HH:MM:SS.mmm to seconds as float."""

    normalized = ts.strip().replace(",", ".")
    parts = normalized.split(":")
    if len(parts) != 3:
        raise ValueError(f"Invalid timestamp: {ts!r}")
    h, m, s = parts
    hours = int(h)
    minutes = int(m)
    seconds = float(s)
    return hours * 3600 + minutes * 60 + seconds


def _maybe_float(raw: str) -> float | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return float(Decimal(raw))
    except (InvalidOperation, ValueError):
        try:
            return float(raw.replace(",", "."))
        except ValueError:
            return None


_FONTISH_TAG = re.compile(r"</?font[^>]*>", re.IGNORECASE)
_RE_FRAMECNT = re.compile(r"FrameCnt\s*:\s*(\d+)", re.IGNORECASE)
_RE_DIFFTIME_MS = re.compile(r"DiffTime\s*:\s*(\d+)\s*ms", re.IGNORECASE)
_RE_CAPTURE_DT = re.compile(r"\b(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\b")
_RE_BRACKET_INNERS = re.compile(r"\[([^\]]+)\]")


def _shutter_to_float(token: str) -> tuple[str | None, float | None]:
    """
    Return (raw_token, numeric value).

    Exposure written as a/b is converted to seconds via a/b; plain numbers are kept as scalars
    (matching legacy DJI SRT Shutter fields that use integers like 60).
    """

    stripped = token.strip()
    if not stripped:
        return None, None
    frac = re.match(
        r"^([-+]?\d+(?:\.\d+)?)\s*/\s*([-+]?\d+(?:\.\d+)?)\s*$",
        stripped,
    )
    if frac:
        num = _maybe_float(frac.group(1))
        den = _maybe_float(frac.group(2))
        if num is not None and den not in (None, 0.0):
            return stripped, num / den
        return stripped, None
    v = _maybe_float(stripped)
    return stripped, v


def _split_kv_chain(s: str) -> dict[str, str]:
    """Parse 'k: v k2: v2' inside one bracket segment."""

    out: dict[str, str] = {}
    i = 0
    n = len(s)
    while i < n:
        m = re.match(r"\s*(\w+)\s*:\s*", s[i:])
        if not m:
            break
        key = m.group(1)
        start = i + m.end()
        nm = re.search(r"\s+(\w+)\s*:\s*", s[start:])
        if nm:
            val = s[start : start + nm.start()].strip()
            i = start + nm.start()
        else:
            val = s[start:n].strip()
            i = n
        if val:
            out[key] = val
    return out


def _header_font_meta(cleaned: str) -> dict[str, Any]:
    """Subtitle header lines stripped of font tags (FrameCnt / DiffTime / capture timestamp)."""

    meta: dict[str, Any] = {}
    mf = _RE_FRAMECNT.search(cleaned)
    if mf:
        meta["frame_count"] = int(mf.group(1))
    md = _RE_DIFFTIME_MS.search(cleaned)
    if md:
        meta["diff_time_ms"] = float(md.group(1))
    mc = _RE_CAPTURE_DT.search(cleaned)
    if mc:
        meta["capture_datetime"] = mc.group(1).strip()
    return meta


def _apply_dji_bracket_overlay(raw_text: str, sink: dict[str, Any]) -> None:
    """Merge DJI `<font>` headers and `[key: value]` bracket fields into sink (overrides earlier keys)."""

    cleaned = _FONTISH_TAG.sub("\n", raw_text)
    sink.update(_header_font_meta(cleaned))

    for m in _RE_BRACKET_INNERS.finditer(cleaned):
        inner = m.group(1).strip()
        for lk, raw_val in _split_kv_chain(inner).items():
            k = lk.lower()
            rv = raw_val.strip()
            if k == "shutter":
                sr, sv = _shutter_to_float(rv)
                if sr:
                    sink["shutter_raw"] = sr
                if sv is not None:
                    sink["shutter"] = sv
                continue
            if k == "color_md":
                sink["color_md"] = rv
                continue
            if k in ("framecnt", "frame_cnt"):
                try:
                    sink["frame_count"] = int(float(rv.replace(",", ".")))
                except ValueError:
                    pass
                continue
            if k == "rel_alt":
                v = _maybe_float(rv)
                if v is not None:
                    sink["rel_altitude"] = v
                continue
            if k == "abs_alt":
                v = _maybe_float(rv)
                if v is not None:
                    sink["altitude_m"] = v
                continue
            if k in {"iso", "ev", "fnum", "focal_len", "ct", "latitude", "longitude"}:
                v = _maybe_float(rv)
                if v is not None:
                    sink[k] = v


def _split_blocks(lines: list[str]) -> list[list[str]]:
    """
    Group lines into SRT cues.

    Standard grammar: index, timestamp, one+ payload lines, blank separator.

    Robustness:
    - Strips BOM on first line
    - Skips extra blanks between cues
    - If index line is missing but a timestamp line appears, synthesize a monotonic index
    """
    if lines and lines[0].startswith("\ufeff"):
        lines[0] = lines[0].lstrip("\ufeff")

    i = 0
    cues: list[list[str]] = []
    synthetic_counter = 0

    while i < len(lines):
        while i < len(lines) and lines[i].strip() == "":
            i += 1
        if i >= len(lines):
            break

        block_lines: list[str] = []
        line = lines[i]
        stripped = line.strip()

        if _TIMESTAMP_LINE.match(stripped):
            synthetic_counter += 1
            block_lines.append(str(synthetic_counter))
            block_lines.append(stripped)
            i += 1
        else:
            if not stripped.isdigit():
                i += 1
                continue
            block_lines.append(stripped)
            i += 1
            if i >= len(lines):
                break
            ts_line = lines[i].strip()
            if not _TIMESTAMP_LINE.match(ts_line):
                i += 1
                continue
            block_lines.append(ts_line)
            i += 1

        payloads: list[str] = []
        while i < len(lines) and lines[i].strip() != "":
            payloads.append(lines[i])
            i += 1
        block_lines.extend(payloads)
        if i < len(lines) and lines[i].strip() == "":
            i += 1
        cues.append(block_lines)

    return cues


_RE_GPS = re.compile(
    r"GPS\s*\(\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)\s*(?:,\s*([-+]?\d+(?:\.\d+)?))?\s*\)",
    re.IGNORECASE,
)
_RE_HOME = re.compile(
    r"HOME\s*\(\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)\s*\)",
    re.IGNORECASE,
)


def _parse_kv_floats(text: str) -> dict[str, Any]:
    """Extract common DJI key:value style fields from raw cue text (legacy line-based cues)."""

    out: dict[str, Any] = {}

    def set_from(pattern: str, key: str, flags: int = 0) -> None:
        m = re.search(pattern, text, flags)
        if not m:
            return
        g = m.group(m.lastindex or 1)
        v = _maybe_float(str(g))
        if v is not None:
            out.setdefault(key, v)

    set_from(r"\b(latitude)\s*[:\[=]\s*([-+]?\d+(?:\.\d+)?)", "latitude", re.IGNORECASE)
    set_from(r"\b(longitude)\s*[:\[=]\s*([-+]?\d+(?:\.\d+)?)", "longitude", re.IGNORECASE)
    set_from(r"\b(lat)\s*[:\[=]\s*([-+]?\d+(?:\.\d+)?)", "latitude", re.IGNORECASE)
    set_from(r"\b(lon|lng)\s*[:\[=]\s*([-+]?\d+(?:\.\d+)?)", "longitude", re.IGNORECASE)
    set_from(r"\baltitude\b\s*[:\[=]\s*([-+]?\d+(?:\.\d+)?)", "altitude_m", re.IGNORECASE)
    set_from(r"\babs_alt\b\s*[:\[=]\s*([-+]?\d+(?:\.\d+)?)", "altitude_m", re.IGNORECASE)
    set_from(r"\brel_alt\b\s*[:\[=]\s*([-+]?\d+(?:\.\d+)?)", "rel_altitude", re.IGNORECASE)
    set_from(r"\brel_altitude\b\s*[:\[=]\s*([-+]?\d+(?:\.\d+)?)", "rel_altitude_m", re.IGNORECASE)
    set_from(r"BAROMETER\s*[:\s]\s*([-+]?\d+(?:\.\d+)?)", "barometer", re.IGNORECASE)
    set_from(r"\bISO\s*[:\s]\s*([-+]?\d+(?:\.\d+)?)", "iso", re.IGNORECASE)
    shutter_m = re.search(r"\bShutter\s*[:\s]+\s*(\S+)", text, re.IGNORECASE)
    if shutter_m:
        sr, sv = _shutter_to_float(shutter_m.group(1))
        if sr:
            out.setdefault("shutter_raw", sr)
        if sv is not None:
            out.setdefault("shutter", sv)
    set_from(r"\bEV\s*[:\s]\s*([-+]?\d+(?:\.\d+)?)", "ev", re.IGNORECASE)
    set_from(r"Fnum\s*[:\s]\s*([-+]?\d+(?:\.\d+)?)", "fnum", re.IGNORECASE)
    set_from(
        r"(?:gb_pitch|gimbalpitch|pitch)\s*[:\[=]\s*([-+]?\d+(?:\.\d+)?)",
        "gimbal_pitch_deg",
        re.IGNORECASE,
    )
    set_from(r"\bgimbal_roll\b\s*[:\[=]\s*([-+]?\d+(?:\.\d+)?)", "gimbal_roll_deg", re.IGNORECASE)
    set_from(
        r"(?:gimbalyaw|gimbal_yaw|GimbalYaw)\s*[:\[=]\s*([-+]?\d+(?:\.\d+)?)",
        "gimbal_yaw_deg",
        re.IGNORECASE,
    )
    set_from(r"\byaw\b\s*[:\[=]\s*([-+]?\d+(?:\.\d+)?)", "yaw_deg", re.IGNORECASE)
    set_from(r"\bheading\b\s*[:\[]=]\s*([-+]?\d+(?:\.\d+)?)", "heading_deg", re.IGNORECASE)

    return out


def _record_from_parts(
    block_index: int,
    start_raw: str,
    end_raw: str,
    raw_text: str,
) -> TelemetryRecord:
    """Assemble TelemetryRecord from parsed timestamps and payload."""

    parse_timestamp_to_seconds(start_raw.replace(",", "."))
    parse_timestamp_to_seconds(end_raw.replace(",", "."))
    s = parse_timestamp_to_seconds(start_raw)
    e = parse_timestamp_to_seconds(end_raw)

    g = _RE_GPS.search(raw_text)
    gps_lon = _maybe_float(g.group(1)) if g else None
    gps_lat = _maybe_float(g.group(2)) if g else None
    gps_alt = None
    if g and len(g.groups()) >= 3 and g.group(3):
        gps_alt = _maybe_float(g.group(3))

    h = _RE_HOME.search(raw_text)
    home_lon = _maybe_float(h.group(1)) if h else None
    home_lat = _maybe_float(h.group(2)) if h else None

    sink: dict[str, Any] = dict(_parse_kv_floats(raw_text))
    _apply_dji_bracket_overlay(raw_text, sink)

    def gf(name: str) -> float | None:
        v = sink.get(name)
        if v is None:
            return None
        if isinstance(v, bool):
            return None
        if isinstance(v, (int, float)):
            f = float(v)
            return f if math.isfinite(f) else None
        if isinstance(v, str):
            return _maybe_float(v)
        return None

    def gf_coerce_lon_lat(name: str) -> float | None:
        """Same as gf but rejects implausible geographic magnitudes (>360) from bad parses."""

        f = gf(name)
        if f is None:
            return None
        if abs(f) > 360.0:
            return None
        return f

    latitude_f = gf_coerce_lon_lat("latitude")
    longitude_f = gf_coerce_lon_lat("longitude")

    if gps_lon is None and longitude_f is not None:
        gps_lon = longitude_f
    if gps_lat is None and latitude_f is not None:
        gps_lat = latitude_f

    altitude_m_f = gf("altitude_m")
    if gps_alt is None and altitude_m_f is not None:
        gps_alt = altitude_m_f

    frame_count_raw = sink.get("frame_count")
    frame_i: int | None = None
    if isinstance(frame_count_raw, int):
        frame_i = frame_count_raw
    elif isinstance(frame_count_raw, float) and frame_count_raw == int(frame_count_raw):
        frame_i = int(frame_count_raw)
    elif isinstance(frame_count_raw, str):
        try:
            frame_i = int(frame_count_raw.strip())
        except ValueError:
            frame_i = None

    shutter_raw = sink.get("shutter_raw")
    shutter_raw_s = str(shutter_raw).strip() if shutter_raw not in (None, "") else None

    cap_raw = sink.get("capture_datetime")
    capture_dt = cap_raw.strip() if isinstance(cap_raw, str) and cap_raw.strip() else None

    color_raw = sink.get("color_md")
    color_clean = color_raw.strip() if isinstance(color_raw, str) and color_raw.strip() else None

    return TelemetryRecord(
        block_index=block_index,
        start_time_raw=start_raw,
        end_time_raw=end_raw,
        start_time_seconds=s,
        end_time_seconds=e,
        raw_text=raw_text,
        home_lon=home_lon,
        home_lat=home_lat,
        gps_lon=gps_lon,
        gps_lat=gps_lat,
        gps_alt=gps_alt,
        barometer=gf("barometer"),
        iso=gf("iso"),
        shutter=gf("shutter"),
        ev=gf("ev"),
        fnum=gf("fnum"),
        latitude=latitude_f,
        longitude=longitude_f,
        altitude_m=altitude_m_f,
        rel_altitude_m=gf("rel_altitude_m"),
        rel_altitude=gf("rel_altitude"),
        gimbal_pitch_deg=gf("gimbal_pitch_deg"),
        gimbal_roll_deg=gf("gimbal_roll_deg"),
        gimbal_yaw_deg=gf("gimbal_yaw_deg"),
        yaw_deg=gf("yaw_deg"),
        heading_deg=gf("heading_deg"),
        frame_count=frame_i,
        diff_time_ms=gf("diff_time_ms"),
        capture_datetime=capture_dt,
        color_md=color_clean,
        focal_len=gf("focal_len"),
        ct=gf("ct"),
        shutter_raw=shutter_raw_s,
    )


def parse_dji_srt(text: str) -> list[TelemetryRecord]:
    """
    Parse DJI-ish SRT; raises SrtParseError if no cues could be built.

    input: Full .srt file contents as string.
    output: Non-empty TelemetryRecord list.
    """

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    blocks = _split_blocks(lines)

    records: list[TelemetryRecord] = []
    seen_index: set[int] = set()

    for block_lines in blocks:
        if len(block_lines) < 2:
            continue
        idx_line = block_lines[0].strip()
        ts_line = block_lines[1].strip()
        m_ts = _TIMESTAMP_LINE.match(ts_line)
        if not m_ts:
            continue
        try:
            bi = int(idx_line)
        except ValueError:
            continue
        if bi in seen_index:
            continue
        seen_index.add(bi)
        start_raw, end_raw = m_ts.group(1), m_ts.group(2)
        payload_lines = block_lines[2:]
        raw_text = "\n".join(payload_lines).strip()
        try:
            rec = _record_from_parts(bi, start_raw, end_raw, raw_text)
        except ValueError:
            continue
        records.append(rec)

    records.sort(key=lambda r: (r.start_time_seconds, r.block_index))

    if not records:
        raise SrtParseError(
            "No valid SRT subtitle cues were found. Check file format "
            "(index line, timestamp line with '-->', payload, blank separator)."
        )
    return records


def telemetry_field_names(record: TelemetryRecord) -> Iterable[str]:
    """Iterable of field names excluding raw/display-only keys."""

    for k in TelemetryRecord.model_fields.keys():
        if k in ("raw_text", "start_time_raw", "end_time_raw"):
            continue
        yield k


def build_fields_detected(records: list[TelemetryRecord]) -> list[str]:
    """Sorted list of field names present (non-null) in at least one record."""

    names: set[str] = set()
    for rec in records:
        for fname in telemetry_field_names(rec):
            v = getattr(rec, fname)
            if v is None:
                continue
            if isinstance(v, float) and not math.isfinite(v):
                continue
            if isinstance(v, str) and not v.strip():
                continue
            names.add(fname)
    return sorted(names)


def build_summary(records: list[TelemetryRecord]) -> FlightSummary:
    """Compute aggregate summary from parsed records."""

    gps_points = sum(
        1
        for r in records
        if r.gps_lat is not None
        and r.gps_lon is not None
        and math.isfinite(r.gps_lat)
        and math.isfinite(r.gps_lon)
    )
    last_end = max((r.end_time_seconds for r in records), default=None)
    home_lat = next((r.home_lat for r in records if r.home_lat is not None), None)
    home_lon = next((r.home_lon for r in records if r.home_lon is not None), None)
    return FlightSummary(
        record_count=len(records),
        gps_point_count=gps_points,
        duration_seconds_srt_end=last_end,
        home_lat=home_lat,
        home_lon=home_lon,
    )


def records_to_jsonable(records: list[TelemetryRecord]) -> list[dict[str, Any]]:
    """Serialize records for JSON export."""

    return [r.model_dump() for r in records]
