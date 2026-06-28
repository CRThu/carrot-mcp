"""Tests for carrot_mcp_pdf.server module."""

import inspect
from unittest.mock import MagicMock, patch

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

def test_get_pages_file_not_found():
    result = get_pages("nonexistent.pdf", "1-5")
    assert result["status"] == "error"
    assert "not found" in result["message"].lower()


def test_get_pages_invalid_range():
    result = get_pages("nonexistent.pdf", "invalid")
    assert result["status"] == "error"


def test_get_pages_out_of_range(tmp_path):
    pdf = tmp_path / "small.pdf"
    pdf.write_bytes(b"fake pdf")

    with patch("carrot_mcp_pdf.server.get_total_pages", return_value=3):
        with patch("carrot_mcp_pdf.server.load_cache", return_value={"pages": {}}):
            result = get_pages(str(pdf), "1-5")

    assert result["status"] == "error"
    assert "out of range" in result["message"].lower()


def test_get_pages_negative_page_range(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")
    result = get_pages(str(pdf), "0")
    assert result["status"] == "error"


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

    assert result["status"] == "ok"
    assert result["pages"]["1"]["content"] == [{"type": "text", "data": "cached"}]


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

    assert result["status"] == "ok"
    assert result["pages"]["1"]["content"] == [{"type": "text", "data": "ocr text"}]


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

    assert result["status"] == "ok"
    assert result["pages"]["1"]["content"] == [{"type": "text", "data": "ocr result"}]


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

    assert result["status"] == "ok"
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

    assert result["status"] == "ok"
    assert result["pages"]["1"]["content"] == [{"type": "text", "data": "existing ocr"}]


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
        "start_time": "2025-01-01T00:00:00",
    }}

    with patch("carrot_mcp_pdf.server._find_task_in_files", return_value=tasks["test_task_123"]):
        result = get_status("test_task_123")

    assert result["status"] == "ok"
    assert result["conversion_status"] == "running"
    assert result["progress_percent"] == 42
    assert result["current_page"] == 5
    assert result["total_pages"] == 10
