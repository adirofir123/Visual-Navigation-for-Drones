"""
Export trajectories as KML for Google Earth (the project's GIS requirement).

KML stores coordinates as ``longitude,latitude[,altitude]`` (lon first). Each named
track becomes a coloured LineString plus a folder of point placemarks, so you can
open the file in Google Earth (desktop or web) and see the estimated path laid over
satellite imagery next to the true (SRT) path.
"""

from __future__ import annotations

from pathlib import Path

# AABBGGRR (KML colour order). A few readable defaults.
_COLORS = {
    "true": "ff1d9e1d",       # green
    "estimated": "ff1775ba",   # orange/blue
    "reference": "ff888780",   # grey
}


def _track_kml(name: str, latlon: list[tuple[float, float]], color: str) -> str:
    coords = " ".join(f"{lon},{lat},0" for lat, lon in latlon)
    points = "\n".join(
        f'    <Placemark><name>{name} {i}</name><styleUrl>#{name}_pt</styleUrl>'
        f"<Point><coordinates>{lon},{lat},0</coordinates></Point></Placemark>"
        for i, (lat, lon) in enumerate(latlon)
    )
    return f"""  <Folder><name>{name}</name>
    <Style id="{name}_ln"><LineStyle><color>{color}</color><width>3</width></LineStyle></Style>
    <Style id="{name}_pt"><IconStyle><color>{color}</color><scale>0.5</scale></IconStyle></Style>
    <Placemark><name>{name} path</name><styleUrl>#{name}_ln</styleUrl>
      <LineString><tessellate>1</tessellate><coordinates>{coords}</coordinates></LineString>
    </Placemark>
{points}
  </Folder>"""


def write_trajectory_kml(
    path: str | Path,
    tracks: dict[str, list[tuple[float, float]]],
) -> Path:
    """
    tracks: {name -> [(lat, lon), ...]}. Names matching 'true'/'estimated'/'reference'
    get preset colours; anything else falls back to grey.
    """
    path = Path(path)
    body = "\n".join(
        _track_kml(name, pts, _COLORS.get(name, "ff888780"))
        for name, pts in tracks.items() if pts
    )
    kml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>\n'
        f"  <name>{path.stem}</name>\n{body}\n</Document></kml>\n"
    )
    path.write_text(kml, encoding="utf-8")
    return path
