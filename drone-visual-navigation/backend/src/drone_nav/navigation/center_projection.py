"""
Project the image-centre ray to the ground ("where is the drone looking?").

Ex1 asks for the coordinate of the centre point of the video. For a camera tilted
``tilt_deg`` below the horizon at height ``h`` above ground, the centre ray meets
the ground at a horizontal range:

        range = h / tan(tilt)            (tilt measured from the horizontal)

in the direction the camera faces (heading). We do not have a per-frame yaw field
stored in the reference rows, so heading is estimated from the *motion direction*
of the trajectory -- valid for a forward-moving drone with a forward-tilted gimbal,
and fully self-contained (no extra telemetry needed).

Note: tilt is measured from horizontal. A "45 degree" DJI gimbal in this dataset is
45 deg below horizontal -> range = h (e.g. 120 m ahead at 120 m height).
"""

from __future__ import annotations

import math


def heading_from_path(xs: list[float], ys: list[float], smooth: int = 2) -> list[float]:
    """
    Per-index heading (radians, ENU: 0 = +x/east, pi/2 = +y/north) from motion.

    Uses a centred finite difference over a +/- ``smooth`` window to reduce jitter.
    Indices with no usable motion inherit the previous heading.
    """
    n = len(xs)
    headings: list[float] = [0.0] * n
    last = 0.0
    for i in range(n):
        a = max(0, i - smooth)
        b = min(n - 1, i + smooth)
        dx = xs[b] - xs[a]
        dy = ys[b] - ys[a]
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            headings[i] = last
        else:
            last = math.atan2(dy, dx)
            headings[i] = last
    return headings


def look_at_point(
    x_m: float,
    y_m: float,
    heading_rad: float,
    height_m: float,
    tilt_deg: float,
) -> tuple[float, float]:
    """
    Ground intersection of the camera centre ray, in the same ENU frame as (x, y).

    A near-nadir camera (tilt -> 90 deg) looks almost straight down (range -> 0);
    a shallow tilt looks far ahead (range grows). Clamped to avoid blow-up.
    """
    tilt = math.radians(max(1.0, min(89.0, tilt_deg)))
    rng = height_m / math.tan(tilt)
    return x_m + rng * math.cos(heading_rad), y_m + rng * math.sin(heading_rad)
