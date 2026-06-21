#!/usr/bin/env python3
"""
Ex1 preliminary experiment -- visual localization vs SRT ground truth.

Two experiments are run against a reference map built from one flight:

  cross-flight : query frames come from a DIFFERENT flight over the same area
                 (the realistic "new flight, no GNSS" test Ex1 describes).
  leave-one-out: query frames are reference frames themselves, with a temporal
                 window around each query removed from the map (a sanity check;
                 its error floor is roughly the map's frame spacing in metres).

For every query we estimate position visually (no GNSS) and compare against the
SRT-derived true position. Outputs: a trajectory plot (estimated vs true) and a
metrics summary (mean / median / p90 error, and recall@{25,50,100} m).

Usage:
  python scripts/run_ex1_experiment.py \
      --map-dir   Dataset/preprocessed/DJI_20260427152226_0017_D/reference \
      --query-dir Dataset/preprocessed/DJI_20260427152735_0019_D/reference \
      --out-dir   experiments/ex1 \
      --query-stride 2 --max-queries 30
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
from drone_nav.navigation.localizer import Localizer  # noqa: E402


def equirect_m(lat1, lon1, lat2, lon2) -> float:
    """Small-angle ground distance in metres between two lat/lon points."""
    lat0 = math.radians((lat1 + lat2) / 2.0)
    dx = math.radians(lon2 - lon1) * 6_371_000.0 * math.cos(lat0)
    dy = math.radians(lat2 - lat1) * 6_371_000.0
    return math.hypot(dx, dy)


def latlon_to_local(lat, lon, lat0, lon0) -> tuple[float, float]:
    """Project lat/lon into a local ENU (metres) frame anchored at (lat0, lon0)."""
    x = (lon - lon0) * 111_320.0 * math.cos(math.radians(lat0))
    y = (lat - lat0) * 111_320.0
    return x, y


def nearest_ref_distance_m(lat, lon, ref_latlon) -> float:
    return min(equirect_m(lat, lon, rlat, rlon) for rlat, rlon in ref_latlon)


def summarize(errors: list[float]) -> dict:
    if not errors:
        return {"n": 0}
    a = np.array(errors, dtype=float)
    return {
        "n": int(a.size),
        "mean_m": round(float(a.mean()), 1),
        "median_m": round(float(np.median(a)), 1),
        "p90_m": round(float(np.percentile(a, 90)), 1),
        "max_m": round(float(a.max()), 1),
        "recall@25m": round(float((a <= 25).mean()), 2),
        "recall@50m": round(float((a <= 50).mean()), 2),
        "recall@100m": round(float((a <= 100).mean()), 2),
    }


def run_cross_flight(localizer, qmap, ref_latlon, *, coverage_m, stride, max_q, min_inliers):
    results = []
    queries = [e for e in qmap.entries if e.lat is not None][::stride]
    used = 0
    for e in queries:
        if used >= max_q:
            break
        if nearest_ref_distance_m(e.lat, e.lon, ref_latlon) > coverage_m:
            continue  # query is outside mapped territory -> no correct answer exists
        t0 = time.time()
        r = localizer.localize(e.kp_xy, e.descriptors)
        dt = time.time() - t0
        if r.est_lat is None:
            continue
        err = equirect_m(e.lat, e.lon, r.est_lat, r.est_lon)
        results.append({
            "query_frame": e.frame_index,
            "true_lat": e.lat, "true_lon": e.lon,
            "est_lat": r.est_lat, "est_lon": r.est_lon,
            "matched_frame": r.matched_frame_index,
            "n_inliers": r.n_inliers, "confident": r.confident,
            "error_m": round(err, 1), "seconds": round(dt, 2),
        })
        used += 1
        print(f"  q{e.frame_index:>6}  inliers={r.n_inliers:>4}  "
              f"err={err:6.1f} m  {'OK ' if r.confident else 'low'}  ({dt:.1f}s)")
    return results


def run_leave_one_out(localizer, rmap, *, exclude_window_s, stride, max_q):
    results = []
    entries = rmap.entries[::stride]
    used = 0
    for e in entries:
        if used >= max_q:
            break
        if e.lat is None:
            continue
        excl = {o.frame_index for o in rmap.entries
                if abs(o.timestamp_s - e.timestamp_s) <= exclude_window_s}
        r = localizer.localize(e.kp_xy, e.descriptors, exclude_frame_indices=excl)
        if r.est_lat is None:
            continue
        err = equirect_m(e.lat, e.lon, r.est_lat, r.est_lon)
        results.append({
            "query_frame": e.frame_index, "true_lat": e.lat, "true_lon": e.lon,
            "est_lat": r.est_lat, "est_lon": r.est_lon,
            "matched_frame": r.matched_frame_index, "n_inliers": r.n_inliers,
            "confident": r.confident, "error_m": round(err, 1),
        })
        used += 1
        print(f"  loo q{e.frame_index:>6}  inliers={r.n_inliers:>4}  err={err:6.1f} m")
    return results


def plot(rmap, qmap, cross, out_png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lat0, lon0 = rmap.origin_lat, rmap.origin_lon
    rx = [latlon_to_local(e.lat, e.lon, lat0, lon0)[0] for e in rmap.entries if e.lat]
    ry = [latlon_to_local(e.lat, e.lon, lat0, lon0)[1] for e in rmap.entries if e.lat]

    fig, ax = plt.subplots(figsize=(9, 7))
    ax.plot(rx, ry, "-", color="#1D9E75", lw=1.5, label="reference map (flight 0017)")

    first_t = first_e = True
    for r in cross:
        tx, ty = latlon_to_local(r["true_lat"], r["true_lon"], lat0, lon0)
        ex, ey = latlon_to_local(r["est_lat"], r["est_lon"], lat0, lon0)
        ax.plot([tx, ex], [ty, ey], "-", color="#888780", lw=0.6, zorder=1)
        ax.scatter([tx], [ty], s=28, color="#185FA5", zorder=3,
                   label="query true (flight 0019)" if first_t else None)
        col = "#BA7517" if r["confident"] else "#E24B4A"
        ax.scatter([ex], [ey], s=28, marker="x", color=col, zorder=3,
                   label="estimated" if first_e else None)
        first_t = first_e = False

    ax.set_aspect("equal", "box")
    ax.set_xlabel("east (m)"); ax.set_ylabel("north (m)")
    ax.set_title("Ex1 cross-flight visual localization vs SRT ground truth")
    ax.legend(loc="best", fontsize=9); ax.grid(True, alpha=0.3)
    fig.tight_layout(); fig.savefig(out_png, dpi=130)
    print(f"  wrote {out_png}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--map-dir", required=True, type=Path)
    p.add_argument("--query-dir", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--query-stride", type=int, default=2)
    p.add_argument("--max-queries", type=int, default=30)
    p.add_argument("--coverage-m", type=float, default=45.0)
    p.add_argument("--min-inliers", type=int, default=20)
    p.add_argument("--loo-window-s", type=float, default=6.0)
    p.add_argument("--loo-max", type=int, default=20)
    p.add_argument("--skip-loo", action="store_true")
    ns = p.parse_args()

    ns.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading reference map: {ns.map_dir}")
    rmap = ReferenceMap.load(ns.map_dir)
    print(f"  {len(rmap)} reference frames")
    print(f"Loading query flight:  {ns.query_dir}")
    qmap = ReferenceMap.load(ns.query_dir)
    print(f"  {len(qmap)} query frames")

    localizer = Localizer(rmap, top_k=5, min_inliers=ns.min_inliers)
    ref_latlon = [(e.lat, e.lon) for e in rmap.entries if e.lat is not None]

    print("\n[cross-flight] localizing flight-0019 frames against the 0017 map:")
    cross = run_cross_flight(
        localizer, qmap, ref_latlon,
        coverage_m=ns.coverage_m, stride=ns.query_stride,
        max_q=ns.max_queries, min_inliers=ns.min_inliers,
    )

    loo = []
    if not ns.skip_loo:
        print("\n[leave-one-out] localizing 0017 frames against 0017 (neighbours removed):")
        loo = run_leave_one_out(
            localizer, rmap,
            exclude_window_s=ns.loo_window_s, stride=ns.query_stride, max_q=ns.loo_max,
        )

    metrics = {
        "map_dir": str(ns.map_dir), "query_dir": str(ns.query_dir),
        "reference_frames": len(rmap),
        "cross_flight": summarize([r["error_m"] for r in cross]),
        "cross_flight_confident_only":
            summarize([r["error_m"] for r in cross if r["confident"]]),
        "leave_one_out": summarize([r["error_m"] for r in loo]),
        "params": {
            "coverage_m": ns.coverage_m, "min_inliers": ns.min_inliers,
            "query_stride": ns.query_stride, "loo_window_s": ns.loo_window_s,
        },
    }
    (ns.out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (ns.out_dir / "cross_flight_results.json").write_text(json.dumps(cross, indent=2))

    if cross:
        plot(rmap, qmap, cross, ns.out_dir / "trajectory.png")

    print("\n===== METRICS =====")
    print(json.dumps(metrics["cross_flight"], indent=2))
    print("confident-only:", json.dumps(metrics["cross_flight_confident_only"]))
    print("leave-one-out :", json.dumps(metrics["leave_one_out"]))
    print(f"\nWrote results to {ns.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
