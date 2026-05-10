"""
Exploratory helpers for DJI ``.DAT`` / flight log binaries.

This does not implement a full DAT parser. Use for quick heuristics only.
"""

from __future__ import annotations

import json
import string
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_DEFAULT_KEYWORDS = (
    "gimbal",
    "pitch",
    "yaw",
    "roll",
    "heading",
    "baro",
    "barometer",
    "home",
    "attitude",
    "quaternion",
    "gps",
    "latitude",
    "longitude",
    "mavlink",
    "dji",
)


@dataclass
class DatInspectionResult:
    dat_path: str
    size_bytes: int
    extension: str
    printable_ratio_sample: float | None
    ascii_snippet_count: int
    keyword_hits: dict[str, bool]
    classification: str
    message: str
    manual_tools: str
    strings_sample_path: str | None = None


def _printable_ratio(blob: bytes) -> float:
    if not blob:
        return 0.0
    good = sum(32 <= b < 127 or b in (9, 10, 13) for b in blob)
    return float(good) / float(len(blob))


def _extract_readable_strings(blob: bytes, *, min_len: int = 4) -> list[bytes]:
    """Contiguous printable ASCII runs (cheap stand-in for ``strings``)."""

    printable = set(bytes(string.printable, "ascii"))
    runs: list[bytes] = []
    cur: list[int] = []
    for b in blob:
        if b in printable and b != 0:
            cur.append(b)
        else:
            if len(cur) >= min_len:
                runs.append(bytes(cur))
            cur = []
    if len(cur) >= min_len:
        runs.append(bytes(cur))
    return runs


MANUAL_TOOLS_BLURB = (
    "External options (manual use): DatCon desktop tool; CSVView / PhantomHelp-style viewers for "
    "some DJI exports; FlightRecordDecryptor / community parsers for encrypted newer logs; "
    "DJI FlightRecordParsingLib / open-source parsers on GitHub (device and firmware dependent). "
    "Many Air-series logs require vendor decryption before structured fields are readable."
)


def inspect_dat_file(
    dat_path: Path,
    *,
    read_limit_bytes: int = 8_388_608,
    strings_sample_max_lines: int = 500,
    strings_sample_max_chars: int = 200_000,
    keywords: tuple[str, ...] = _DEFAULT_KEYWORDS,
) -> tuple[DatInspectionResult, str]:
    """
    Return (structured result, full strings sample body for ``.txt``).

    Missing file yields a graceful result with classification ``missing``.
    """

    p = dat_path
    if not p.is_file():
        res = DatInspectionResult(
            dat_path=str(p),
            size_bytes=0,
            extension=p.suffix.lower(),
            printable_ratio_sample=None,
            ascii_snippet_count=0,
            keyword_hits={k: False for k in keywords},
            classification="missing",
            message="DAT path does not exist or is not a file.",
            manual_tools=MANUAL_TOOLS_BLURB,
            strings_sample_path=None,
        )
        return res, ""

    size = p.stat().st_size
    to_read = min(size, read_limit_bytes) if read_limit_bytes > 0 else size
    try:
        with p.open("rb") as fh:
            head = fh.read(to_read)
    except OSError as e:
        res = DatInspectionResult(
            dat_path=str(p.resolve()),
            size_bytes=size,
            extension=p.suffix.lower(),
            printable_ratio_sample=None,
            ascii_snippet_count=0,
            keyword_hits={k: False for k in keywords},
            classification="unreadable",
            message=f"Could not read file: {e}",
            manual_tools=MANUAL_TOOLS_BLURB,
        )
        return res, ""

    ratio = _printable_ratio(head)
    runs = _extract_readable_strings(head)
    sample_lines: list[str] = []
    total_chars = 0
    for rb in runs:
        try:
            s = rb.decode("ascii", errors="ignore").strip()
        except Exception:
            continue
        if not s:
            continue
        sample_lines.append(s)
        total_chars += len(s) + 1
        if len(sample_lines) >= strings_sample_max_lines or total_chars >= strings_sample_max_chars:
            break

    joined_lower = "\n".join(sample_lines).lower()
    latin_blob = head.decode("latin-1", errors="ignore").lower()
    hits = {k: (k.lower() in latin_blob or k.lower() in joined_lower) for k in keywords}

    low_printable = ratio < 0.15
    few_strings = len(sample_lines) < 8
    keyword_any = any(hits.values())

    if low_printable and not keyword_any:
        classification = "not_directly_parseable"
        message = (
            "DAT file is not directly parseable by this project pipeline. "
            "Continue with SRT + manual metadata fallback."
        )
    elif few_strings and not keyword_any:
        classification = "not_directly_parseable"
        message = (
            "DAT file is not directly parseable by this project pipeline. "
            "Continue with SRT + manual metadata fallback."
        )
    elif keyword_any:
        classification = "maybe_textual_hints"
        message = (
            "Some human-readable tokens matching telemetry keywords were found in a binary sample. "
            "A full parser or external tool is still required to extract structured fields."
        )
    else:
        classification = "unknown_binary"
        message = (
            "Binary sample did not match quick heuristics. "
            "Treat as not directly parseable unless external tools succeed."
        )

    res = DatInspectionResult(
        dat_path=str(p.resolve()),
        size_bytes=size,
        extension=p.suffix.lower(),
        printable_ratio_sample=round(ratio, 6),
        ascii_snippet_count=len(sample_lines),
        keyword_hits=hits,
        classification=classification,
        message=message,
        manual_tools=MANUAL_TOOLS_BLURB,
        strings_sample_path=None,
    )
    body = "\n".join(sample_lines)
    return res, body


def result_to_json_dict(res: DatInspectionResult) -> dict[str, Any]:
    d = asdict(res)
    return d


def write_inspection_outputs(
    result: DatInspectionResult,
    strings_body: str,
    output_dir: Path,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "dat_inspection_summary.json"
    strings_path = output_dir / "dat_strings_sample.txt"
    summary_dict = result_to_json_dict(result)
    summary_dict["strings_sample_path"] = strings_path.name
    summary_path.write_text(json.dumps(summary_dict, indent=2), encoding="utf-8")
    strings_path.write_text(strings_body, encoding="utf-8")
    return summary_path, strings_path

