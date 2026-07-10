"""Tests for carrot_mcp_pdf.converter module."""

import base64
from unittest.mock import MagicMock, patch

from carrot_mcp_pdf.converter import (
    get_total_pages,
    parse_page_content,
    read_image,
    render_page_as_image,
)


# ── read_image ───────────────────────────────────────────────────────────────

def test_read_image(tmp_path):
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    data, mime = read_image(str(img))
    assert isinstance(data, bytes)
    assert data.startswith(b"\x89PNG")
    assert mime == "image/png"


def test_read_image_jpeg(tmp_path):
    img = tmp_path / "photo.jpg"
    img.write_bytes(b"\xff\xd8\xff" + b"\x00" * 100)

    data, mime = read_image(str(img))
    assert isinstance(data, bytes)
    assert data.startswith(b"\xff\xd8\xff")
    assert mime == "image/jpeg"


def test_read_image_unknown_ext(tmp_path):
    img = tmp_path / "img.xyz"
    img.write_bytes(b"\x00" * 100)

    _, mime = read_image(str(img))
    assert mime == "image/jpeg"  # default


# ── parse_page_content ───────────────────────────────────────────────────────

def test_parse_page_content_text_only():
    content = parse_page_content("Hello world", "/nonexistent")
    assert len(content) == 1
    assert content[0] == {"type": "text", "data": "Hello world"}


def test_parse_page_content_no_images():
    content = parse_page_content("Line 1\n\nLine 2", "/nonexistent")
    assert len(content) == 1
    assert "Line 1" in content[0]["data"]


def test_parse_page_content_image_not_found(tmp_path):
    text = "Text before ![img](missing.png) text after"
    content = parse_page_content(text, str(tmp_path))
    assert len(content) == 2
    assert content[0]["type"] == "text"
    assert "Text before" in content[0]["data"]
    assert content[1]["type"] == "text"
    assert "text after" in content[1]["data"]


def test_parse_page_content_with_image(tmp_path):
    img = tmp_path / "photo.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

    text = "Before ![img](photo.png) After"
    content = parse_page_content(text, str(tmp_path))
    assert len(content) == 3
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image"
    assert isinstance(content[1]["data"], str)
    assert base64.b64decode(content[1]["data"]).startswith(b"\x89PNG")
    assert content[1]["mime"] == "image/png"
    assert content[2]["type"] == "text"


def test_parse_page_content_data_uri_skipped():
    text = "Text ![img](data:image/png;base64,abc) more"
    content = parse_page_content(text, "/nonexistent")
    assert len(content) == 2
    assert content[0] == {"type": "text", "data": "Text"}
    assert content[1] == {"type": "text", "data": "more"}
    for b in content:
        assert "data:image/png" not in b.get("data", "")


def test_parse_page_content_empty_text():
    content = parse_page_content("", "/nonexistent")
    assert content == []


# ── get_total_pages ──────────────────────────────────────────────────────────

def test_get_total_pages_from_cache():
    cache = {"total_pages": 42}
    assert get_total_pages("/fake.pdf", cache) == 42


def test_get_total_pages_zero_no_file(tmp_path):
    cache = {"total_pages": 0}
    result = get_total_pages(str(tmp_path / "nonexistent.pdf"), cache)
    assert result == 0


# ── render_page_as_image ─────────────────────────────────────────────────────

def test_render_page_as_image_returns_png():
    with patch("carrot_mcp_pdf.converter.pymupdf") as mock_pdf:
        mock_page = MagicMock()
        mock_pix = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix
        mock_doc = MagicMock()
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        mock_pdf.open.return_value = mock_doc
        mock_pdf.Matrix.return_value = MagicMock()

        with patch("tempfile.mkstemp", return_value=(0, "/tmp/test.png")):
            result = render_page_as_image("/fake.pdf", 1)

    assert result == "/tmp/test.png"
