"""ORB feature extraction edge cases."""

import numpy as np
import pytest

pytest.importorskip("cv2")

from pathlib import Path

from drone_nav.features.orb_features import extract_orb_to_npz


def test_orb_blank_image_writes_empty_npz(tmp_path: Path) -> None:
    gray = np.zeros((64, 64, 3), dtype=np.uint8)
    outp = tmp_path / "empty.npz"
    n = extract_orb_to_npz(gray, outp)
    assert n == 0
    assert outp.is_file()
    z = np.load(outp)
    assert z["kp_xy"].shape == (0, 2)
    assert z["descriptor"].shape[0] == 0
