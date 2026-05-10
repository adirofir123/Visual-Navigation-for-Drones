#!/usr/bin/env python3
"""Exploratory DJI DAT inspection — does not decode structured telemetry."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve()
_PROJECT_ROOT = _SCRIPT.parents[1]
_BACKEND_ROOT = _PROJECT_ROOT / "backend"
for _p in (_BACKEND_ROOT, _BACKEND_ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def main() -> int:
    from drone_nav.preprocessing.dat_inspector import inspect_dat_file, write_inspection_outputs

    p = argparse.ArgumentParser(description="Heuristic DAT / flight log inspector.")
    p.add_argument("--dat", type=Path, required=True, help="Path to .DAT flight log.")
    p.add_argument("--output", type=Path, required=True, help="Output directory for reports.")
    args = p.parse_args()

    try:
        res, body = inspect_dat_file(args.dat)
        summary_path, strings_path = write_inspection_outputs(res, body, args.output)
        print(f"Summary: {summary_path}")
        print(f"strings: {strings_path}")
        print(f"classification={res.classification}")
        print(res.message)
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
