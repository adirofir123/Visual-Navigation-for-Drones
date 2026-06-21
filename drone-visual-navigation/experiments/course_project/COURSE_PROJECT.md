# Course project — upgrading the Ex1 visual navigation baseline

The course project extends Ex1 ("design a real-time visual navigation algorithm
based on predefined annotated previous videos, and GIS datasets"). It keeps the
Ex1 place-recognition core and adds three things: a **diagnosis** of where the
error actually comes from, a **sequential motion-gated localizer** that fixes the
biggest failure mode, and a **GIS / Google Earth** export.

## 1. What we measured first (this drove the design)

Before adding anything, we measured *why* the Ex1 baseline is off by ~45-70 m on
the cross-flight test:

| quantity | value | meaning |
| --- | --- | --- |
| oracle nearest-reference error | ~18 m | the map is dense; the best possible "snap" is ~18 m |
| matched-reference error | ~67 m | what the matcher actually achieves |
| retrieval gap (matched − oracle) | ~41 m | the matcher often picks a wrong-but-similar frame |
| catastrophic fixes (>120 m) | ~18% | gross mis-matches ("teleports") to a far, similar-looking place |

Conclusion: the bottleneck is **retrieval picking the wrong reference**, not
coarse map spacing. We also tried homography-based metric refinement (correcting
the position by the pixel shift × ground-sampling-distance); it *worsened* error,
because the 45° camera tilt breaks the single-scale assumption. That negative
result is reported honestly and is a good thing to be able to explain.

## 2. Upgrade A — sequential motion-gated localization (`sequential_localizer.py`)

A drone moves continuously, so a fix implying an impossible jump from the last
position is almost certainly a wrong match. This is the **Monte-Carlo /
particle-filter localization** idea from the literature review, in its simplest
(gating) form:

1. Keep the last accepted position and time.
2. Predict the next position is within `max_speed * dt + margin` metres.
3. Among the visually-verified candidates, prefer those inside that gate.
4. If none is plausible, **reject and coast** (output no fix rather than a wrong one).
5. If a *very strong* global match appears, **re-acquire** (recover from loss).

### Result (24 in-coverage queries, one matching pass)

| metric | baseline | sequential | change |
| --- | --- | --- | --- |
| mean error | 90.5 m | 72.9 m | −19% |
| **p90 error** | **208.7 m** | **89.6 m** | **−57%** |
| max error | 262.7 m | 228.6 m | lower |
| recall @ 100 m | 0.81 | 0.92 | +11 pts |

The headline is the **p90 dropping from ~209 m to ~90 m**: the filter removes the
catastrophic teleports. Median is similar, because gating does not fix the basic
retrieval gap — that needs either stronger retrieval (DINOv2) or motion
propagation (visual odometry). Both are documented below as the next tier.

## 3. Upgrade B — GIS / Google Earth export (`kml_export.py`)

The estimated path and the true (SRT) path are written to `estimated_path.kml`.
Open it in Google Earth (desktop or web) to see the visually-estimated trajectory
laid over satellite imagery next to ground truth. This is the project's explicit
"GIS datasets (such as Google Earth)" requirement, and it doubles as an intuitive
visual for the presentation.

## 4. How to run

```bash
cd drone-visual-navigation
python scripts/run_course_project.py \
  --map-dir   Dataset/preprocessed/DJI_20260427152226_0017_D/reference \
  --query-dir Dataset/preprocessed/DJI_20260427152735_0019_D/reference \
  --out-dir   experiments/course_project --max-queries 24
```

Outputs in `experiments/course_project/`: `metrics.json`,
`trajectory_compare.png` (true vs baseline vs sequential), and
`estimated_path.kml` (open in Google Earth). Runs on CPU in a few minutes; no raw
video, no GPU.

## 5. Documented next tier (heavier, GPU-dependent — future work)

These are named in the literature review and are the natural continuation; they
were left out because they need a GPU and the current bar is a working pipeline:

- **DINOv2 / NetVLAD global descriptors** for retrieval — one vector per frame and
  fast nearest-neighbour search, which directly attacks the ~41 m retrieval gap.
- **LightGlue + PnP** for metric pose (done properly with camera intrinsics, unlike
  the naive refinement we tried).
- **DPVO visual odometry** to propagate position between visual fixes, which would
  let the motion gate tighten dramatically and fix the median, not just the tail.
- **OSM road-network priors** to constrain estimates to plausible map locations.
