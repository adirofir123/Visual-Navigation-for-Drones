"""
Match a query frame's ORB features against a single reference frame.

Two signals are produced:
  * ``n_good`` -- count of Lowe-ratio-passing descriptor matches (cheap, coarse).
  * ``n_inliers`` -- count of RANSAC-homography inliers (geometric verification).

The coarse score (``n_good``) is used to shortlist candidate references; the
geometric score (``n_inliers``) breaks ties and rejects visually-similar but
geometrically-inconsistent frames (the classic "perceptual aliasing" failure of
place recognition over repetitive aerial scenes).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

try:
    import cv2  # type: ignore
except ImportError:  # pragma: no cover
    cv2 = None


@dataclass(frozen=True)
class PairMatch:
    n_good: int          # ratio-test survivors
    n_inliers: int       # homography inliers (0 if homography failed)
    inlier_ratio: float  # n_inliers / max(n_good, 1)
    homography: np.ndarray | None  # 3x3 query->reference pixel map, or None


def _bf() -> "cv2.BFMatcher":
    # Hamming distance is the correct metric for binary ORB descriptors.
    # crossCheck=False because we run an explicit ratio test instead.
    return cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)


def count_good_matches(
    desc_q: np.ndarray,
    desc_r: np.ndarray,
    *,
    ratio: float = 0.75,
) -> int:
    """Cheap coarse score: number of ratio-test survivors (no geometry)."""
    if cv2 is None:
        raise RuntimeError("OpenCV is required for ORB matching.")
    if desc_q is None or desc_r is None or len(desc_q) < 2 or len(desc_r) < 2:
        return 0
    knn = _bf().knnMatch(desc_q, desc_r, k=2)
    good = 0
    for pair in knn:
        if len(pair) < 2:
            continue
        m, n = pair
        if m.distance < ratio * n.distance:
            good += 1
    return good


def match_pair(
    desc_q: np.ndarray,
    kp_q: np.ndarray,
    desc_r: np.ndarray,
    kp_r: np.ndarray,
    *,
    ratio: float = 0.75,
    ransac_reproj_px: float = 5.0,
    min_good_for_homography: int = 8,
) -> PairMatch:
    """
    Compare query descriptors/keypoints against one reference frame.

    desc_*: (N, 32) uint8 ORB descriptors.
    kp_*:   (N, 2) float32 pixel coordinates aligned with descriptors.
    """
    if cv2 is None:
        raise RuntimeError("OpenCV is required for ORB matching.")

    if desc_q is None or desc_r is None or len(desc_q) < 2 or len(desc_r) < 2:
        return PairMatch(0, 0, 0.0, None)

    # KNN (k=2) + Lowe ratio test: keep a match only if the best neighbour is
    # clearly closer than the second best -> rejects ambiguous descriptors.
    knn = _bf().knnMatch(desc_q, desc_r, k=2)
    good = []
    for pair in knn:
        if len(pair) < 2:
            continue
        m, n = pair
        if m.distance < ratio * n.distance:
            good.append(m)

    n_good = len(good)
    if n_good < min_good_for_homography:
        return PairMatch(n_good, 0, 0.0, None)

    src = np.float32([kp_q[m.queryIdx] for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kp_r[m.trainIdx] for m in good]).reshape(-1, 1, 2)

    H, mask = cv2.findHomography(src, dst, cv2.RANSAC, ransac_reproj_px)
    if H is None or mask is None:
        return PairMatch(n_good, 0, 0.0, None)

    n_inliers = int(mask.sum())
    return PairMatch(
        n_good=n_good,
        n_inliers=n_inliers,
        inlier_ratio=n_inliers / max(n_good, 1),
        homography=H,
    )
