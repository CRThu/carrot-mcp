"""Tests for carrot_mcp_pdf.server module."""

import base64
import json
from unittest.mock import MagicMock, patch

from mcp.types import ImageContent, TextContent

from carrot_mcp_pdf.server import (
    get_pages,
    get_toc,
    mcp,
    version,
)


# ── version ──────────────────────────────────────────────────────────────────

def test_version():
    result = version()
    assert result["status"] == "ok"
    assert result["name"] == "carrot-mcp-pdf"
    assert isinstance(result["version"], str)


# ── MCP server ───────────────────────────────────────────────────────────────

def test_mcp_server_name():
    assert mcp.name == "carrot-mcp-pdf"


def test_mcp_tools_registered():
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "version" in tool_names
    assert "get_toc" in tool_names
    assert "get_pages" in tool_names


# ── get_toc ──────────────────────────────────────────────────────────────────

def test_get_toc_file_not_found():
    result = get_toc("nonexistent.pdf")
    assert result["status"] == "error"
    assert "not found" in result["message"].lower()


def test_get_toc_success(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")

    mock_doc = MagicMock()
    mock_doc.get_toc.return_value = [
        [1, "Chapter 1", 1],
        [1, "Chapter 1", 2],
        [2, "Section 1.1", 3],
    ]
    mock_doc.page_count = 10

    with patch("carrot_mcp_pdf.server.pymupdf.open", return_value=mock_doc), \
         patch("carrot_mcp_pdf.server.load_cache", return_value={"pages": {}}), \
         patch("carrot_mcp_pdf.server.save_cache"):
        result = get_toc(str(pdf))

    assert result["status"] == "ok"
    assert result["has_toc"] is True
    assert result["total_pages"] == 10
    assert len(result["toc"]) == 2
    assert result["toc"][0]["title"] == "Chapter 1"
    assert result["toc"][0]["start_page"] == 1
    assert result["toc"][0]["end_page"] == 2


def test_get_toc_no_toc(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")

    mock_doc = MagicMock()
    mock_doc.get_toc.return_value = []
    mock_doc.page_count = 5

    with patch("carrot_mcp_pdf.server.pymupdf.open", return_value=mock_doc), \
         patch("carrot_mcp_pdf.server.load_cache", return_value={"pages": {}}), \
         patch("carrot_mcp_pdf.server.save_cache"):
        result = get_toc(str(pdf))

    assert result["status"] == "ok"
    assert result["has_toc"] is False
    assert result["total_pages"] == 5
    assert "scanned pdf" in result["message"].lower()


# ── get_pages ────────────────────────────────────────────────────────────────

def _parse_result(result: list):
    """Helper to parse get_pages result into (meta_dict, content_blocks)."""
    meta = json.loads(result[0].text)
    return meta, result[1:]


def test_get_pages_file_not_found():
    result = get_pages("nonexistent.pdf", "1-5")
    meta, _ = _parse_result(result)
    assert meta["status"] == "error"
    assert "not found" in meta["message"].lower()


def test_get_pages_invalid_range():
    result = get_pages("nonexistent.pdf", "invalid")
    meta, _ = _parse_result(result)
    assert meta["status"] == "error"


def test_get_pages_out_of_range(tmp_path):
    pdf = tmp_path / "small.pdf"
    pdf.write_bytes(b"fake pdf")

    with patch("carrot_mcp_pdf.server.get_total_pages", return_value=3):
        with patch("carrot_mcp_pdf.server.load_cache", return_value={"pages": {}}):
            result = get_pages(str(pdf), "1-5")

    meta, _ = _parse_result(result)
    assert meta["status"] == "error"
    assert "out of range" in meta["message"].lower()


def test_get_pages_negative_page_range(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")
    result = get_pages(str(pdf), "0")
    meta, _ = _parse_result(result)
    assert meta["status"] == "error"


def test_get_pages_from_cache(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")

    cached = {
        "pages": {
            "1": {"content": [{"type": "text", "data": "cached"}]},
        }
    }

    with patch("carrot_mcp_pdf.server.get_total_pages", return_value=3), \
         patch("carrot_mcp_pdf.server.load_cache", return_value=cached):
        result = get_pages(str(pdf), "1")

    meta, blocks = _parse_result(result)
    assert meta["status"] == "ok"
    assert isinstance(blocks[0], TextContent)
    assert blocks[0].text == "[Page 1]"
    assert isinstance(blocks[1], TextContent)
    assert blocks[1].text == "cached"


def test_get_pages_image_returns_image_content(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")

    img_bytes = b"\x89PNG\r\n\x1a\n"
    cached = {
        "pages": {
            "1": {"content": [
                {"type": "text", "data": "before"},
                {"type": "image", "data": img_bytes, "mime": "image/png"},
                {"type": "text", "data": "after"},
            ]},
        }
    }

    with patch("carrot_mcp_pdf.server.get_total_pages", return_value=3), \
         patch("carrot_mcp_pdf.server.load_cache", return_value=cached):
        result = get_pages(str(pdf), "1")

    meta, blocks = _parse_result(result)
    assert meta["status"] == "ok"
    assert len(blocks) == 4
    assert isinstance(blocks[0], TextContent)
    assert blocks[0].text == "[Page 1]"
    assert isinstance(blocks[1], TextContent)
    assert blocks[1].text == "before"
    assert isinstance(blocks[2], ImageContent)
    assert blocks[2].mimeType == "image/png"
    assert blocks[2].context == "Page 1, image 0"
    assert base64.b64decode(blocks[2].data) == img_bytes
    assert isinstance(blocks[3], TextContent)
    assert blocks[3].text == "after"


def test_get_pages_multiple_images_indexed(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")

    img1 = b"\x89PNG\r\n\x1a\n"
    img2 = b"\x89PNG\r\n\x1a\n\x00"
    cached = {
        "pages": {
            "1": {"content": [
                {"type": "text", "data": "start"},
                {"type": "image", "data": img1, "mime": "image/png"},
                {"type": "text", "data": "middle"},
                {"type": "image", "data": img2, "mime": "image/jpeg"},
                {"type": "text", "data": "end"},
            ]},
        }
    }

    with patch("carrot_mcp_pdf.server.get_total_pages", return_value=3), \
         patch("carrot_mcp_pdf.server.load_cache", return_value=cached):
        result = get_pages(str(pdf), "1")

    meta, blocks = _parse_result(result)
    assert meta["status"] == "ok"
    assert len(blocks) == 6
    assert blocks[0].text == "[Page 1]"
    assert blocks[2].context == "Page 1, image 0"
    assert blocks[2].mimeType == "image/png"
    assert blocks[4].context == "Page 1, image 1"
    assert blocks[4].mimeType == "image/jpeg"


def test_get_pages_extract_text_false_returns_rendered_image(tmp_path):
    """extract_text=False renders pages as images."""
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")

    img_bytes = b"\x89PNG\r\n\x1a\n"

    with patch("carrot_mcp_pdf.server.get_total_pages", return_value=3), \
         patch("carrot_mcp_pdf.server.load_cache", return_value={"pages": {}}), \
         patch("carrot_mcp_pdf.server.render_page_as_image", return_value="/tmp/page.png"), \
         patch("carrot_mcp_pdf.server.read_image", return_value=(img_bytes, "image/png")), \
         patch("carrot_mcp_pdf.server.os.unlink"):
        result = get_pages(str(pdf), "1", extract_text=False)

    meta, blocks = _parse_result(result)
    assert meta["status"] == "ok"
    assert blocks[0].text == "[Page 1]"
    assert isinstance(blocks[1], ImageContent)
    assert blocks[1].mimeType == "image/png"
    assert blocks[1].context == "Page 1"
    assert base64.b64decode(blocks[1].data) == img_bytes


def test_get_pages_extract_text_false_multiple_pages(tmp_path):
    """extract_text=False renders each page as a separate image."""
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")

    img_bytes = b"\x89PNG\r\n\x1a\n"

    def render_side_effect(path, page_num):
        return f"/tmp/page_{page_num}.png"

    with patch("carrot_mcp_pdf.server.get_total_pages", return_value=3), \
         patch("carrot_mcp_pdf.server.load_cache", return_value={"pages": {}}), \
         patch("carrot_mcp_pdf.server.render_page_as_image", side_effect=render_side_effect), \
         patch("carrot_mcp_pdf.server.read_image", return_value=(img_bytes, "image/png")), \
         patch("carrot_mcp_pdf.server.os.unlink"):
        result = get_pages(str(pdf), "1-2", extract_text=False)

    meta, blocks = _parse_result(result)
    assert meta["status"] == "ok"
    # 2 pages * (1 TextContent + 1 ImageContent) = 4
    assert len(blocks) == 4
    assert blocks[0].text == "[Page 1]"
    assert isinstance(blocks[1], ImageContent)
    assert blocks[2].text == "[Page 2]"
    assert isinstance(blocks[3], ImageContent)


def test_get_pages_pymupdf4llm_returns_str(tmp_path):
    """Test that get_pages handles pymupdf4llm.to_markdown() returning str."""
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")

    with patch("carrot_mcp_pdf.server.get_total_pages", return_value=3), \
         patch("carrot_mcp_pdf.server.load_cache", return_value={"pages": {}}), \
         patch("carrot_mcp_pdf.server.save_cache"), \
         patch("carrot_mcp_pdf.server.pymupdf4llm.to_markdown", return_value="Hello world"):
        result = get_pages(str(pdf), "1")

    meta, blocks = _parse_result(result)
    assert meta["status"] == "ok"
    assert blocks[0].text == "[Page 1]"
    assert blocks[1].text == "Hello world"


def test_get_pages_pymupdf4llm_returns_list(tmp_path):
    """Test that get_pages handles pymupdf4llm.to_markdown() returning list[dict]."""
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")

    with patch("carrot_mcp_pdf.server.get_total_pages", return_value=3), \
         patch("carrot_mcp_pdf.server.load_cache", return_value={"pages": {}}), \
         patch("carrot_mcp_pdf.server.save_cache"), \
         patch("carrot_mcp_pdf.server.pymupdf4llm.to_markdown", return_value=[{"text": "Page content", "metadata": {}}]):
        result = get_pages(str(pdf), "1")

    meta, blocks = _parse_result(result)
    assert meta["status"] == "ok"
    assert blocks[1].text == "Page content"


# ── grep ────────────────────────────────────────────────────────────────────


def test_grep_basic(tmp_path):
    """Test basic grep functionality."""
    import pymupdf
    pdf = tmp_path / "grep.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello World")
    page.insert_text((72, 100), "Goodbye World")
    doc.save(str(pdf))
    doc.close()

    from carrot_mcp_pdf.server import grep
    result = grep(str(pdf), "Hello")
    assert result["status"] == "ok"
    assert result["count"] == 1
    assert result["matches"][0]["page"] == 1
    assert "Hello" in result["matches"][0]["text"]


def test_grep_case_insensitive(tmp_path):
    """Test case-insensitive grep."""
    import pymupdf
    pdf = tmp_path / "grep_ci.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello World")
    doc.save(str(pdf))
    doc.close()

    from carrot_mcp_pdf.server import grep
    result = grep(str(pdf), "hello")
    assert result["status"] == "ok"
    assert result["count"] == 1


def test_grep_no_match(tmp_path):
    """Test grep with no matches."""
    import pymupdf
    pdf = tmp_path / "grep_nomatch.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello World")
    doc.save(str(pdf))
    doc.close()

    from carrot_mcp_pdf.server import grep
    result = grep(str(pdf), "xyz")
    assert result["status"] == "ok"
    assert result["count"] == 0
    assert result["matches"] == []


def test_grep_regex(tmp_path):
    """Test regex grep."""
    import pymupdf
    pdf = tmp_path / "grep_regex.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "abc 123")
    page.insert_text((72, 100), "xyz 456")
    doc.save(str(pdf))
    doc.close()

    from carrot_mcp_pdf.server import grep
    result = grep(str(pdf), r"abc \d+", regex=True)
    assert result["status"] == "ok"
    assert result["count"] == 1


def test_grep_regex_invalid(tmp_path):
    """Test invalid regex returns error."""
    import pymupdf
    pdf = tmp_path / "grep_regex_invalid.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "test")
    doc.save(str(pdf))
    doc.close()

    from carrot_mcp_pdf.server import grep
    result = grep(str(pdf), r"[invalid", regex=True)
    assert result["status"] == "error"
    assert "Invalid regex" in result["message"]


def test_grep_file_not_found():
    """Test grep with non-existent file."""
    from carrot_mcp_pdf.server import grep
    result = grep("/nonexistent/file.pdf", "test")
    assert result["status"] == "error"
    assert "File not found" in result["message"]
