"""
Localize a single query frame against a ReferenceMap.

Pipeline (hierarchical, matching the literature-review design at a classical tier):

  1. Coarse retrieval -- score every reference by ratio-test match count (n_good),
     keep the top-K candidates.
  2. Geometric verification -- run RANSAC homography on each candidate; the one with
     the most inliers wins (rejects perceptual aliasing).
  3. Position estimate -- the winning reference's known georeferenced position is
     returned as the drone's estimated position (place-recognition baseline).

``confident`` is False when the best candidate has too few inliers; callers should
treat low-confidence fixes as "no fix" rather than trusting a bad match.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from drone_nav.matching.orb_matcher import count_good_matches, match_pair
from drone_nav.navigation.reference_index import ReferenceEntry, ReferenceMap


@dataclass
class LocalizationResult:
    matched_frame_index: int | None
    est_x: float | None
    est_y: float | None
    est_lat: float | None
    est_lon: float | None
    n_good: int
    n_inliers: int
    confident: bool
    candidate_frame_indices: list[int]  # the shortlist that was geometrically checked


class Localizer:
    def __init__(
        self,
        reference_map: ReferenceMap,
        *,
        top_k: int = 5,
        ratio: float = 0.75,
        min_inliers: int = 20,
    ) -> None:
        self.map = reference_map
        self.top_k = top_k
        self.ratio = ratio
        self.min_inliers = min_inliers

    def localize(
        self,
        kp_q: np.ndarray,
        desc_q: np.ndarray,
        *,
        exclude_frame_indices: set[int] | None = None,
    ) -> LocalizationResult:
        exclude = exclude_frame_indices or set()
        candidates = [e for e in self.map.entries if e.frame_index not in exclude]

        # --- Stage 1: coarse scoring by ratio-test match count (no geometry) ---
        coarse: list[tuple[int, ReferenceEntry]] = []
        for e in candidates:
            n_good = count_good_matches(desc_q, e.descriptors, ratio=self.ratio)
            coarse.append((n_good, e))
        coarse.sort(key=lambda t: t[0], reverse=True)
        shortlist = [e for _, e in coarse[: self.top_k]]

        # --- Stage 2: geometric verification on the shortlist ---
        best: ReferenceEntry | None = None
        best_inliers = -1
        best_good = 0
        for e in shortlist:
            pm = match_pair(desc_q, kp_q, e.descriptors, e.kp_xy, ratio=self.ratio)
            if pm.n_inliers > best_inliers:
                best_inliers = pm.n_inliers
                best_good = pm.n_good
                best = e

        if best is None:
            return LocalizationResult(
                None, None, None, None, None, 0, 0, False,
                [e.frame_index for e in shortlist],
            )

        est_lat, est_lon = best.lat, best.lon
        if (est_lat is None or est_lon is None) and best.local_x is not None:
            est_lat, est_lon = self.map.local_to_latlon(best.local_x, best.local_y)

        return LocalizationResult(
            matched_frame_index=best.frame_index,
            est_x=best.local_x,
            est_y=best.local_y,
            est_lat=est_lat,
            est_lon=est_lon,
            n_good=best_good,
            n_inliers=max(best_inliers, 0),
            confident=best_inliers >= self.min_inliers,
            candidate_frame_indices=[e.frame_index for e in shortlist],
        )
