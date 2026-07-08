"""Tests for carrot_mcp_pdf.cache module."""

import pytest

from carrot_mcp_pdf.cache import (
    get_cache_path,
    load_cache,
    parse_page_range,
    save_cache,
)


# ── parse_page_range ─────────────────────────────────────────────────────────

def test_parse_page_range_single():
    assert parse_page_range("1") == [1]


def test_parse_page_range_int_single():
    assert parse_page_range(1) == [1]


def test_parse_page_range_int_large():
    assert parse_page_range(100) == [100]


def test_parse_page_range_int_zero_raises():
    with pytest.raises(ValueError, match=">= 1"):
        parse_page_range(0)


def test_parse_page_range_int_negative_raises():
    with pytest.raises(ValueError, match=">= 1"):
        parse_page_range(-1)


def test_parse_page_range_none():
    assert parse_page_range(None) == []


def test_parse_page_range_list_ints():
    assert parse_page_range([1, 3, 5]) == [1, 3, 5]


def test_parse_page_range_list_strs():
    assert parse_page_range(["1-3", "5"]) == [1, 2, 3, 5]


def test_parse_page_range_list_mixed():
    assert parse_page_range([1, "3-5", 8]) == [1, 3, 4, 5, 8]


def test_parse_page_range_list_empty():
    assert parse_page_range([]) == []


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


# ── paths ────────────────────────────────────────────────────────────────────

def test_get_cache_path_ends_with_json():
    assert get_cache_path("test.pdf").endswith(".json")


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


def test_save_cache_creates_dirs(tmp_path):
    pdf = tmp_path / "sub" / "dir" / "test.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"fake pdf")

    data = {"name": "test.pdf", "total_pages": 1}
    save_cache(str(pdf), data)
    loaded = load_cache(str(pdf))
    assert loaded["total_pages"] == 1
