"""
Build Google Earth-compatible KML for GPS path.

Coordinates use KML ordering: longitude,latitude,altitude relative to WGS84.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from xml.dom import minidom

from app.telemetry.telemetry_schema import TelemetryRecord


def _finite_pair(r: TelemetryRecord) -> tuple[float, float, float] | None:
    if r.gps_lon is None or r.gps_lat is None:
        return None
    if not math.isfinite(r.gps_lon) or not math.isfinite(r.gps_lat):
        return None
    alt = r.gps_alt if r.gps_alt is not None and math.isfinite(r.gps_alt) else 0.0
    return (r.gps_lon, r.gps_lat, alt)


def telemetry_to_kml_bytes(records: list[TelemetryRecord], *, name: str = "Flight path") -> bytes:
    """
    Create KML document with LineString path and start/end placemarks.

    input: telemetry records; rows without valid GPS are skipped.
    output: pretty-printed UTF-8 KML bytes.
    """

    coords: list[tuple[float, float, float]] = []
    for r in records:
        p = _finite_pair(r)
        if p:
            coords.append(p)

    kml = ET.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    doc = ET.SubElement(kml, "Document")
    ET.SubElement(doc, "name").text = name

    if len(coords) >= 2:
        ls_pm = ET.SubElement(doc, "Placemark")
        ET.SubElement(ls_pm, "name").text = "Path"
        line = ET.SubElement(ls_pm, "LineString")
        ET.SubElement(line, "tessellate").text = "1"
        coord_text = " ".join(f"{lon},{lat},{alt}" for lon, lat, alt in coords)
        ET.SubElement(line, "coordinates").text = coord_text

    if coords:
        start_lon, start_lat, start_alt = coords[0]
        sp = ET.SubElement(doc, "Placemark")
        ET.SubElement(sp, "name").text = "Start"
        ps = ET.SubElement(sp, "Point")
        ET.SubElement(ps, "coordinates").text = f"{start_lon},{start_lat},{start_alt}"

    if len(coords) >= 2:
        end_lon, end_lat, end_alt = coords[-1]
        ep = ET.SubElement(doc, "Placemark")
        ET.SubElement(ep, "name").text = "End"
        pe = ET.SubElement(ep, "Point")
        ET.SubElement(pe, "coordinates").text = f"{end_lon},{end_lat},{end_alt}"

    rough = ET.tostring(kml, encoding="utf-8")
    dom = minidom.parseString(rough)
    return dom.toprettyxml(indent="  ", encoding="utf-8")
