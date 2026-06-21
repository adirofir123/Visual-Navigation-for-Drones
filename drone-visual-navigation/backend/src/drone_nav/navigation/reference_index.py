"""
Load a preprocessed reference dataset into an in-memory, searchable map.

Consumes exactly what ``reference_builder`` already produced:
  * ``reference_frames.json`` -- per-frame georeferenced metadata.
  * ``features/frame_XXXXXX_orb.npz`` -- per-frame ORB keypoints + descriptors.
  * ``reference_summary.json`` -- dataset-level origin (lat0/lon0 of the ENU frame).

No raw video and no GNSS are needed at query time -- this is the "visual memory"
bank the navigation stage searches against.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class ReferenceEntry:
    frame_index: int
    timestamp_s: float
    image_path: str
    lat: float | None
    lon: float | None
    local_x: float | None     # ENU east (m) relative to dataset origin
    local_y: float | None     # ENU north (m)
    rel_alt_m: float | None
    camera_angle_deg: float | None
    kp_xy: np.ndarray         # (N, 2) float32
    descriptors: np.ndarray   # (N, 32) uint8


@dataclass
class ReferenceMap:
    root: Path
    reference_id: str
    origin_lat: float | None
    origin_lon: float | None
    entries: list[ReferenceEntry] = field(default_factory=list)

    @classmethod
    def load(cls, reference_dir: str | Path) -> "ReferenceMap":
        root = Path(reference_dir).resolve()
        frames = json.loads((root / "reference_frames.json").read_text())
        summary = json.loads((root / "reference_summary.json").read_text())

        entries: list[ReferenceEntry] = []
        for row in frames:
            feat_rel = row.get("feature_path")
            if not feat_rel or row.get("feature_status") != "extracted":
                continue  # only frames with usable ORB features join the map
            npz = np.load(root / feat_rel)
            kp = npz["kp_xy"]
            desc = npz["descriptor"]
            if desc is None or len(desc) == 0:
                continue
            entries.append(
                ReferenceEntry(
                    frame_index=int(row["frame_index"]),
                    timestamp_s=float(row["timestamp_seconds"]),
                    image_path=row["image_path"],
                    lat=row.get("drone_lat"),
                    lon=row.get("drone_lon"),
                    local_x=row.get("local_x_m"),
                    local_y=row.get("local_y_m"),
                    rel_alt_m=row.get("rel_alt_m"),
                    camera_angle_deg=row.get("manual_camera_angle_deg"),
                    kp_xy=kp.astype(np.float32),
                    descriptors=desc.astype(np.uint8),
                )
            )

        entries.sort(key=lambda e: e.timestamp_s)
        return cls(
            root=root,
            reference_id=str(summary.get("reference_id", "")),
            origin_lat=summary.get("origin_lat_deg"),
            origin_lon=summary.get("origin_lon_deg"),
            entries=entries,
        )

    # --- ENU <-> geographic helpers (equirectangular, fine over a few km) ---

    def local_to_latlon(self, x_m: float, y_m: float) -> tuple[float | None, float | None]:
        if self.origin_lat is None or self.origin_lon is None:
            return None, None
        lat0 = math.radians(self.origin_lat)
        dlat = y_m / 111_320.0
        dlon = x_m / (111_320.0 * math.cos(lat0))
        return self.origin_lat + dlat, self.origin_lon + dlon

    def __len__(self) -> int:
        return len(self.entries)
