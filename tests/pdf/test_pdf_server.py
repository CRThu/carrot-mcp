"""Tests for carrot_mcp_pdf.server module."""

import base64
import inspect
import json
from unittest.mock import MagicMock, patch

from mcp.types import ImageContent, TextContent

from carrot_mcp_pdf.server import (
    create_task,
    get_pages,
    get_status,
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
    assert "vlm_model" in result
    assert "vlm_configured" in result
    assert isinstance(result["vlm_configured"], bool)


def test_version_vlm_configured():
    with patch("carrot_mcp_pdf.server.VISION_MODEL", "gpt-4o"), \
         patch("carrot_mcp_pdf.server.VISION_API_KEY", "key"):
        result = version()
        assert result["vlm_model"] == "gpt-4o"
        assert result["vlm_configured"] is True


def test_version_vlm_not_configured():
    with patch("carrot_mcp_pdf.server.VISION_MODEL", None), \
         patch("carrot_mcp_pdf.server.VISION_API_KEY", None):
        result = version()
        assert result["vlm_model"] is None
        assert result["vlm_configured"] is False


def test_version_vlm_partial():
    with patch("carrot_mcp_pdf.server.VISION_MODEL", "gpt-4o"), \
         patch("carrot_mcp_pdf.server.VISION_API_KEY", None):
        result = version()
        assert result["vlm_configured"] is False


# ── MCP server ───────────────────────────────────────────────────────────────

def test_mcp_server_name():
    assert mcp.name == "carrot-mcp-pdf"


def test_mcp_tools_registered():
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "version" in tool_names
    assert "get_toc" in tool_names
    assert "get_pages" in tool_names
    assert "create_task" in tool_names
    assert "get_status" in tool_names


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
            "1": {"content": [{"type": "text", "data": "cached"}], "ocr_content": [{"type": "text", "data": "ocr"}]},
        }
    }

    with patch("carrot_mcp_pdf.server.get_total_pages", return_value=3), \
         patch("carrot_mcp_pdf.server.load_cache", return_value=cached):
        result = get_pages(str(pdf), "1", multimodal=True)

    meta, blocks = _parse_result(result)
    assert meta["status"] == "ok"
    assert isinstance(blocks[0], TextContent)
    assert blocks[0].text == "[Page 1]"
    assert isinstance(blocks[1], TextContent)
    assert blocks[1].text == "cached"


def test_get_pages_multimodal_false_returns_ocr(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")

    cached = {
        "pages": {
            "1": {"content": [{"type": "text", "data": "base64 img"}], "ocr_content": [{"type": "text", "data": "ocr text"}]},
        }
    }

    with patch("carrot_mcp_pdf.server.get_total_pages", return_value=3), \
         patch("carrot_mcp_pdf.server.load_cache", return_value=cached):
        result = get_pages(str(pdf), "1", multimodal=False)

    meta, blocks = _parse_result(result)
    assert meta["status"] == "ok"
    assert blocks[0].text == "[Page 1]"
    assert blocks[1].text == "ocr text"


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
            ], "ocr_content": [{"type": "text", "data": "ocr text"}]},
        }
    }

    with patch("carrot_mcp_pdf.server.get_total_pages", return_value=3), \
         patch("carrot_mcp_pdf.server.load_cache", return_value=cached):
        result = get_pages(str(pdf), "1", multimodal=True)

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
            ], "ocr_content": [{"type": "text", "data": "ocr"}]},
        }
    }

    with patch("carrot_mcp_pdf.server.get_total_pages", return_value=3), \
         patch("carrot_mcp_pdf.server.load_cache", return_value=cached):
        result = get_pages(str(pdf), "1", multimodal=True)

    meta, blocks = _parse_result(result)
    assert meta["status"] == "ok"
    assert len(blocks) == 6
    assert blocks[0].text == "[Page 1]"
    assert blocks[2].context == "Page 1, image 0"
    assert blocks[2].mimeType == "image/png"
    assert blocks[4].context == "Page 1, image 1"
    assert blocks[4].mimeType == "image/jpeg"


def test_get_pages_force_ocr_returns_ocr_content(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")

    cached = {
        "force_ocr": True,
        "pages": {
            "1": {"content": [{"type": "text", "data": "ocr result"}], "ocr_content": [{"type": "text", "data": "ocr result"}]},
        }
    }

    with patch("carrot_mcp_pdf.server.get_total_pages", return_value=3), \
         patch("carrot_mcp_pdf.server.load_cache", return_value=cached):
        result = get_pages(str(pdf), "1", multimodal=True)

    meta, blocks = _parse_result(result)
    assert meta["status"] == "ok"
    assert blocks[0].text == "[Page 1]"
    assert blocks[1].text == "ocr result"


def test_get_pages_force_ocr_clears_cache(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")

    old_cache = {
        "pages": {
            "1": {"content": [{"type": "text", "data": "old garbled"}], "ocr_content": []},
            "2": {"content": [{"type": "text", "data": "old garbled"}], "ocr_content": []},
        }
    }

    with patch("carrot_mcp_pdf.server.get_total_pages", return_value=3), \
         patch("carrot_mcp_pdf.server.load_cache", return_value=old_cache), \
         patch("carrot_mcp_pdf.server.save_cache") as mock_save, \
         patch("carrot_mcp_pdf.server.ocr_page", return_value=[{"type": "text", "data": "new ocr"}]):
        result = get_pages(str(pdf), "1", force_ocr=True)

    meta, blocks = _parse_result(result)
    assert meta["status"] == "ok"
    saved_cache = mock_save.call_args[0][1]
    assert saved_cache["force_ocr"] is True
    assert saved_cache["pages"]["1"] == {"content": [{"type": "text", "data": "new ocr"}], "ocr_content": [{"type": "text", "data": "new ocr"}]}


def test_get_pages_force_ocr_preserves_cache_if_already_set(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")

    old_cache = {
        "force_ocr": True,
        "pages": {
            "1": {"content": [{"type": "text", "data": "existing ocr"}], "ocr_content": [{"type": "text", "data": "existing ocr"}]},
        }
    }

    with patch("carrot_mcp_pdf.server.get_total_pages", return_value=2), \
         patch("carrot_mcp_pdf.server.load_cache", return_value=old_cache), \
         patch("carrot_mcp_pdf.server.save_cache"):
        result = get_pages(str(pdf), "1", force_ocr=True)

    meta, blocks = _parse_result(result)
    assert meta["status"] == "ok"
    assert blocks[0].text == "[Page 1]"
    assert blocks[1].text == "existing ocr"


# ── create_task ──────────────────────────────────────────────────────────────

def test_create_task_file_not_found():
    result = create_task("nonexistent.pdf")
    assert result["status"] == "error"
    assert "not found" in result["message"].lower()


def test_create_task_has_multimodal_param():
    sig = inspect.signature(create_task)
    assert "multimodal" in sig.parameters
    assert sig.parameters["multimodal"].default is True


def test_create_task_success(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")

    with patch("carrot_mcp_pdf.server.get_total_pages", return_value=10), \
         patch("carrot_mcp_pdf.server.load_cache", return_value={"pages": {}}), \
         patch("carrot_mcp_pdf.server.load_tasks", return_value={}), \
         patch("carrot_mcp_pdf.server.save_tasks"), \
         patch("carrot_mcp_pdf.server.threading.Thread") as mock_thread:
        mock_thread.return_value.start = MagicMock()
        result = create_task(str(pdf))

    assert result["status"] == "ok"
    assert "task_id" in result
    assert result["total_pages"] == 10
    assert result["message"] == "Background conversion started"


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


# ── get_status ───────────────────────────────────────────────────────────────

def test_get_status_not_found():
    result = get_status("nonexistent_task_id")
    assert result["status"] == "error"
    assert "not found" in result["message"].lower()


def test_get_status_returns_all_fields(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")

    tasks = {"test_task_123": {
        "status": "running",
        "progress_percent": 42,
        "current_page": 5,
        "total_pages": 10,
        "cached_pages": 4,
        "failed_at_page": 5,
        "start_time": "2025-01-01T00:00:00",
    }}

    with patch("carrot_mcp_pdf.server._find_task_in_files", return_value=tasks["test_task_123"]):
        result = get_status("test_task_123")

    assert result["status"] == "ok"
    assert result["conversion_status"] == "running"
    assert result["progress_percent"] == 42
    assert result["current_page"] == 5
    assert result["total_pages"] == 10
    assert result["cached_pages"] == 4
    assert result["failed_at_page"] == 5


# ── _convert_all task lifecycle ──────────────────────────────────────────────

def test_convert_all_completed_deletes_task(tmp_path):
    from carrot_mcp_pdf.server import _convert_all

    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")
    task_id = "abc123_1234"
    tasks = {task_id: {"status": "running", "progress_percent": 0, "current_page": 0}}

    with patch("carrot_mcp_pdf.server.load_cache", return_value={
        "pages": {}, "force_ocr": True, "total_pages": 2,
    }), \
         patch("carrot_mcp_pdf.server.save_cache"), \
         patch("carrot_mcp_pdf.server.load_tasks", return_value=tasks), \
         patch("carrot_mcp_pdf.server.save_tasks") as mock_save, \
         patch("carrot_mcp_pdf.server.get_total_pages", return_value=2), \
         patch("carrot_mcp_pdf.server.ocr_page", return_value="ocr text"):
        _convert_all(pdf, task_id, multimodal=True, force_ocr=True)

    saved = mock_save.call_args[0][1]
    assert task_id not in saved, "completed task should be deleted from tasks"
