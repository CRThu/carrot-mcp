"""Tests for carrot_mcp_pdf.cache module."""

import pytest

from carrot_mcp_pdf.cache import (
    get_cache_path,
    get_tasks_path,
    load_cache,
    load_tasks,
    make_task_id,
    parse_page_range,
    save_cache,
    save_tasks,
)


# ── parse_page_range ─────────────────────────────────────────────────────────

def test_parse_page_range_single():
    assert parse_page_range("1") == [1]


def test_parse_page_range_range():
    assert parse_page_range("1-5") == [1, 2, 3, 4, 5]


def test_parse_page_range_mixed():
    assert parse_page_range("1-3,5,8-10") == [1, 2, 3, 5, 8, 9, 10]


def test_parse_page_range_duplicates():
    assert parse_page_range("1-3,2-4") == [1, 2, 3, 4]


def test_parse_page_range_with_spaces():
    assert parse_page_range("1 - 3 , 5") == [1, 2, 3, 5]


def test_parse_page_range_negative_raises():
    with pytest.raises(ValueError, match=">= 1"):
        parse_page_range("0")


def test_parse_page_range_zero_raises():
    with pytest.raises(ValueError, match=">= 1"):
        parse_page_range("0-5")


def test_parse_page_range_invalid_order_raises():
    with pytest.raises(ValueError, match="start > end"):
        parse_page_range("5-1")


def test_parse_page_range_non_numeric_raises():
    with pytest.raises(ValueError):
        parse_page_range("abc")


# ── make_task_id ─────────────────────────────────────────────────────────────

def test_make_task_id_format():
    tid = make_task_id("/path/to/test.pdf")
    parts = tid.split("_")
    assert len(parts) == 2
    assert len(parts[0]) == 8
    assert parts[1].isdigit()


def test_make_task_id_deterministic_hash():
    id1 = make_task_id("/path/to/test.pdf")
    id2 = make_task_id("/path/to/test.pdf")
    assert id1.split("_")[0] == id2.split("_")[0]


# ── paths ────────────────────────────────────────────────────────────────────

def test_get_cache_path_ends_with_json():
    assert get_cache_path("test.pdf").endswith(".json")


def test_get_tasks_path_ends_with_tasks_json():
    assert get_tasks_path("test.pdf").endswith("_tasks.json")


def test_different_files_different_paths():
    assert get_cache_path("a.pdf") != get_cache_path("b.pdf")


# ── load/save cache ──────────────────────────────────────────────────────────

def test_load_save_cache_roundtrip(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")

    data = {"name": "test.pdf", "total_pages": 5, "pages": {"1": {"content": []}}}
    save_cache(str(pdf), data)

    loaded = load_cache(str(pdf))
    assert loaded["name"] == "test.pdf"
    assert loaded["total_pages"] == 5
    assert loaded["pages"] == {"1": {"content": []}}


def test_load_cache_returns_copy(tmp_path):
    """Mutating returned dict should not affect cached version."""
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")

    data = {"name": "test.pdf", "total_pages": 5}
    save_cache(str(pdf), data)

    loaded = load_cache(str(pdf))
    loaded["total_pages"] = 999

    loaded2 = load_cache(str(pdf))
    assert loaded2["total_pages"] == 5


def test_load_cache_nonexistent_file(tmp_path):
    pdf = tmp_path / "nonexistent.pdf"
    loaded = load_cache(str(pdf))
    assert loaded["total_pages"] == 0
    assert loaded["pages"] == {}


def test_load_save_tasks_roundtrip(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")

    data = {"task_1": {"status": "running", "progress_percent": 50}}
    save_tasks(str(pdf), data)

    loaded = load_tasks(str(pdf))
    assert loaded["task_1"]["status"] == "running"
    assert loaded["task_1"]["progress_percent"] == 50


def test_load_tasks_returns_copy(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")

    data = {"task_1": {"status": "running"}}
    save_tasks(str(pdf), data)

    loaded = load_tasks(str(pdf))
    loaded["task_1"]["status"] = "done"

    loaded2 = load_tasks(str(pdf))
    assert loaded2["task_1"]["status"] == "running"


def test_save_cache_creates_dirs(tmp_path):
    pdf = tmp_path / "sub" / "dir" / "test.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"fake pdf")

    data = {"name": "test.pdf", "total_pages": 1}
    save_cache(str(pdf), data)
    loaded = load_cache(str(pdf))
    assert loaded["total_pages"] == 1
