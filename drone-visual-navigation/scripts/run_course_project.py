#!/usr/bin/env python3
"""
Course-project experiment -- upgrades over the Ex1 baseline.

Runs two localizers over the same flight-0019 query stream against the flight-0017
reference map, in a single matching pass:

  baseline   : pick the visually strongest reference each frame (Ex1 behaviour).
  sequential : add a motion gate + outlier rejection (SequentialLocalizer) so
               impossible "teleport" fixes are rejected.

Outputs:
  * metrics.json            -- error stats for both localizers
  * trajectory_compare.png  -- true vs baseline vs sequential paths
  * estimated_path.kml      -- estimated + true paths for Google Earth (GIS)

Usage:
  python scripts/run_course_project.py \
      --map-dir   Dataset/preprocessed/DJI_20260427152226_0017_D/reference \
      --query-dir Dataset/preprocessed/DJI_20260427152735_0019_D/reference \
      --out-dir   experiments/course_project --max-queries 30
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

_SCRIPT = Path(__file__).resolve()
_BACKEND = _SCRIPT.parents[1] / "backend"
for _p in (_BACKEND, _BACKEND / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402

from drone_nav.navigation.reference_index import ReferenceMap  # noqa: E402
from drone_nav.matching.orb_matcher import count_good_matches, match_pair  # noqa: E402
from drone_nav.navigation.sequential_localizer import (  # noqa: E402
    Candidate, SequentialLocalizer,
)
from drone_nav.navigation.kml_export import write_trajectory_kml  # noqa: E402


def equirect_m(lat1, lon1, lat2, lon2) -> float:
    lat0 = math.radians((lat1 + lat2) / 2.0)
    dx = math.radians(lon2 - lon1) * 6_371_000.0 * math.cos(lat0)
    dy = math.radians(lat2 - lat1) * 6_371_000.0
    return math.hypot(dx, dy)


def latlon_to_local(lat, lon, lat0, lon0):
    return ((lon - lon0) * 111_320.0 * math.cos(math.radians(lat0)),
            (lat - lat0) * 111_320.0)


def summarize(errs):
    if not errs:
        return {"n": 0}
    a = np.array(errs, float)
    return {
        "n": int(a.size), "mean_m": round(float(a.mean()), 1),
        "median_m": round(float(np.median(a)), 1),
        "p90_m": round(float(np.percentile(a, 90)), 1),
        "max_m": round(float(a.max()), 1),
        "recall@50m": round(float((a <= 50).mean()), 2),
        "recall@100m": round(float((a <= 100).mean()), 2),
    }


def build_candidates(query, refs, top_k=6):
    coarse = sorted(
        ((count_good_matches(query.descriptors, r.descriptors), r) for r in refs),
        key=lambda t: t[0], reverse=True,
    )[:top_k]
    out = []
    for _, r in coarse:
        if r.local_x is None:
            continue
        pm = match_pair(query.descriptors, query.kp_xy, r.descriptors, r.kp_xy)
        out.append(Candidate(pm.n_inliers, r.local_x, r.local_y, r.lat, r.lon))
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--map-dir", required=True, type=Path)
    p.add_argument("--query-dir", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--coverage-m", type=float, default=45.0)
    p.add_argument("--max-queries", type=int, default=30)
    p.add_argument("--min-inliers", type=int, default=12)
    ns = p.parse_args()
    ns.out_dir.mkdir(parents=True, exist_ok=True)

    rmap = ReferenceMap.load(ns.map_dir)
    qmap = ReferenceMap.load(ns.query_dir)
    refs = rmap.entries
    ref_ll = [(e.lat, e.lon) for e in refs if e.lat is not None]
    print(f"map: {len(refs)} frames   query flight: {len(qmap)} frames")

    def in_cov(lat, lon):
        return min(equirect_m(lat, lon, a, b) for a, b in ref_ll) <= ns.coverage_m

    # time-ordered, in-coverage queries (capped, spread across the flight)
    qs = sorted((e for e in qmap.entries if e.lat is not None),
                key=lambda e: e.timestamp_s)
    qs = [e for e in qs if in_cov(e.lat, e.lon)]
    if len(qs) > ns.max_queries:
        qs = qs[:: max(1, len(qs) // ns.max_queries)][: ns.max_queries]

    print(f"scoring {len(qs)} in-coverage queries (one matching pass)...")
    t0 = time.time()
    cached = [(e, build_candidates(e, refs)) for e in qs]
    print(f"  matched in {time.time() - t0:.0f}s")

    seq = SequentialLocalizer(min_inliers=ns.min_inliers)
    base_err, seq_err = [], []
    true_ll, base_ll, seq_ll = [], [], []

    for e, cands in cached:
        valid = [c for c in cands if c.inliers >= ns.min_inliers]
        if not valid:
            continue
        # baseline: strongest visual match, every frame independent
        b = max(valid, key=lambda c: c.inliers)
        base_err.append(equirect_m(e.lat, e.lon, b.lat, b.lon))
        # sequential: motion-gated
        fx = seq.update(cands, e.timestamp_s)
        true_ll.append((e.lat, e.lon))
        base_ll.append((b.lat, b.lon))
        if fx.lat is not None:
            seq_err.append(equirect_m(e.lat, e.lon, fx.lat, fx.lon))
            seq_ll.append((fx.lat, fx.lon))

    metrics = {
        "reference_frames": len(refs),
        "baseline": summarize(base_err),
        "sequential": summarize(seq_err),
    }
    (ns.out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))

    # KML for Google Earth (GIS deliverable)
    kml = write_trajectory_kml(
        ns.out_dir / "estimated_path.kml",
        {"true": true_ll, "estimated": seq_ll,
         "reference": [(e.lat, e.lon) for e in refs if e.lat]},
    )
    print(f"  wrote {kml}")

    # comparison plot
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    lat0, lon0 = rmap.origin_lat, rmap.origin_lon
    rx = [latlon_to_local(e.lat, e.lon, lat0, lon0)[0] for e in refs if e.lat]
    ry = [latlon_to_local(e.lat, e.lon, lat0, lon0)[1] for e in refs if e.lat]
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.plot(rx, ry, "-", color="#1D9E75", lw=1.2, label="reference map (0017)")
    for ll, col, lab, mk in [(true_ll, "#185FA5", "true (0019)", "o"),
                             (base_ll, "#E24B4A", "baseline est", "x"),
                             (seq_ll, "#BA7517", "sequential est", "+")]:
        xy = [latlon_to_local(la, lo, lat0, lon0) for la, lo in ll]
        if xy:
            ax.scatter([a for a, _ in xy], [b for _, b in xy], s=26, marker=mk,
                       color=col, label=lab, zorder=3)
    ax.set_aspect("equal", "box"); ax.set_xlabel("east (m)"); ax.set_ylabel("north (m)")
    ax.set_title("Course project: baseline vs sequential localization")
    ax.legend(fontsize=9); ax.grid(True, alpha=0.3)
    fig.tight_layout(); fig.savefig(ns.out_dir / "trajectory_compare.png", dpi=130)
    print(f"  wrote {ns.out_dir / 'trajectory_compare.png'}")

    print("\n===== METRICS =====")
    print("baseline  :", json.dumps(metrics["baseline"]))
    print("sequential:", json.dumps(metrics["sequential"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
