"""
Sequential (online) localization on top of single-frame visual fixes.

The single-frame Localizer treats every frame independently, so a visually
similar but geographically wrong reference can win -> "teleport" outliers. A real
drone moves continuously, so a fix that implies an impossible jump from the last
known position is almost certainly wrong. This module adds that motion constraint,
which is the core idea of Monte-Carlo / particle-filter localization in its
simplest, gating form:

  * keep the last accepted position + time,
  * predict the next position lies within ``max_speed * dt + margin`` metres,
  * among the visually-verified candidates, prefer those inside that gate,
  * reject (coast) when nothing plausible is available,
  * re-acquire globally when a very strong match appears (recovery from loss).

It does NOT invent a position from nothing -- with no motion sensor we cannot
propagate through long gaps; those are handled by re-acquisition, and tighter
propagation is the documented next step (visual odometry / DPVO).
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    inliers: int
    x: float          # ENU east (m) in the reference-map frame
    y: float          # ENU north (m)
    lat: float
    lon: float


@dataclass(frozen=True)
class Fix:
    x: float | None
    y: float | None
    lat: float | None
    lon: float | None
    inliers: int
    confident: bool
    gated: bool       # True if a motion-gate was applied to pick this fix
    coasted: bool     # True if no plausible fix was found this step


class SequentialLocalizer:
    def __init__(
        self,
        *,
        max_speed_mps: float = 25.0,
        base_margin_m: float = 30.0,
        min_inliers: int = 12,
        reacquire_inliers: int = 60,
    ) -> None:
        self.max_speed = max_speed_mps
        self.margin = base_margin_m
        self.min_inliers = min_inliers
        self.reacquire_inliers = reacquire_inliers
        self._x: float | None = None
        self._y: float | None = None
        self._t: float | None = None

    def reset(self) -> None:
        self._x = self._y = self._t = None

    def update(self, candidates: list[Candidate], timestamp_s: float) -> Fix:
        valid = [c for c in candidates if c.inliers >= self.min_inliers]
        if not valid:
            # nothing trustworthy this step -> coast on the last estimate
            return Fix(self._x, self._y, None, None, 0, False, False, True)

        best_global = max(valid, key=lambda c: c.inliers)

        # cold start, or recovering after a gap: trust the strongest visual fix
        if self._x is None or self._t is None:
            chosen, gated = best_global, False
        else:
            dt = abs(timestamp_s - self._t)
            radius = self.max_speed * dt + self.margin
            in_gate = [
                c for c in valid
                if math.hypot(c.x - self._x, c.y - self._y) <= radius
            ]
            if in_gate:
                chosen, gated = max(in_gate, key=lambda c: c.inliers), True
            elif best_global.inliers >= self.reacquire_inliers:
                # no plausible local fix, but a very strong global match -> re-acquire
                chosen, gated = best_global, False
            else:
                # implausible jump and not strongly supported -> reject, coast
                return Fix(self._x, self._y, None, None, 0, False, True, True)

        self._x, self._y, self._t = chosen.x, chosen.y, timestamp_s
        return Fix(
            chosen.x, chosen.y, chosen.lat, chosen.lon,
            chosen.inliers, chosen.inliers >= self.reacquire_inliers, gated, False,
        )
