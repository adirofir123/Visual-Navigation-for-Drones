"""OpenCV ORB extraction persisted as compressed NumPy archives."""

from __future__ import annotations

from pathlib import Path

import numpy as np

try:
    import cv2  # type: ignore
except ImportError:
    cv2 = None


def extract_orb_to_npz(bgr: np.ndarray, npz_path: Path) -> int:
    """
    Detect ORB keypoints on ``bgr`` image and write ``.npz`` with keys
    ``kp_xy`` (N×2 float32), ``response`` (N float32), ``descriptor`` (N×32 uint8).

    Returns keypoint count (may be zero).
    """

    if cv2 is None:
        raise RuntimeError("OpenCV required for ORB extraction.")

    npz_path.parent.mkdir(parents=True, exist_ok=True)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=1500)
    keypoints, descriptors = orb.detectAndCompute(gray, None)

    if not keypoints:
        kp_xy = np.zeros((0, 2), dtype=np.float32)
        response = np.zeros((0,), dtype=np.float32)
        descr = np.zeros((0, 32), dtype=np.uint8)
    else:
        kp_xy = np.array([[kp.pt[0], kp.pt[1]] for kp in keypoints], dtype=np.float32)
        response = np.array([float(kp.response) for kp in keypoints], dtype=np.float32)
        descr = descriptors if descriptors is not None else np.zeros((len(keypoints), 32), dtype=np.uint8)

    np.savez_compressed(
        npz_path,
        kp_xy=kp_xy,
        response=response,
        descriptor=descr,
    )
    return int(kp_xy.shape[0])
