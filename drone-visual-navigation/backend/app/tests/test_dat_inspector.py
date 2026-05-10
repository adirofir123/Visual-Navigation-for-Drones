"""DAT exploratory inspector."""

import json

from pathlib import Path

from app.preprocessing.dat_inspector import inspect_dat_file, write_inspection_outputs


def test_missing_dat_is_graceful(tmp_path: Path) -> None:
    missing = Path("/nonexistent/path/definitely_missing.DAT")
    res, body = inspect_dat_file(missing)
    assert res.classification == "missing"
    summ, txt = write_inspection_outputs(res, body, tmp_path / "out")
    assert summ.is_file() and txt.is_file()
    data = json.loads(summ.read_text(encoding="utf-8"))
    assert data["classification"] == "missing"
    assert isinstance(data["message"], str)


def test_small_binary_dat_heuristic(tmp_path: Path) -> None:
    tiny = tmp_path / "x.dat"
    tiny.write_bytes(b"\x80\x81binary")
    res, body = inspect_dat_file(tiny, read_limit_bytes=256)
    assert res.classification in (
        "not_directly_parseable",
        "unknown_binary",
        "maybe_textual_hints",
    )
    assert res.size_bytes == len(b"\x80\x81binary")
    assert isinstance(body, str)
