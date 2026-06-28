"""Tests for Carrot MCP PDF Server."""

import copy
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

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
from carrot_mcp_pdf.ocr import recognize_image
from carrot_mcp_pdf.server import (
    _get_total_pages,
    _parse_page_content,
    _read_image_as_base64,
    _resolve_multimodal,
    _vlm_configured,
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


def test_mcp_server_name():
    assert mcp.name == "carrot-mcp-pdf"


def test_mcp_tools_registered():
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "version" in tool_names
    assert "get_toc" in tool_names
    assert "get_pages" in tool_names
    assert "create_task" in tool_names
    assert "get_status" in tool_names


# ── cache.py: parse_page_range ───────────────────────────────────────────────

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
    import pytest
    with pytest.raises(ValueError, match=">= 1"):
        parse_page_range("0")


def test_parse_page_range_zero_raises():
    import pytest
    with pytest.raises(ValueError, match=">= 1"):
        parse_page_range("0-5")


def test_parse_page_range_invalid_order_raises():
    import pytest
    with pytest.raises(ValueError, match="start > end"):
        parse_page_range("5-1")


def test_parse_page_range_non_numeric_raises():
    import pytest
    with pytest.raises(ValueError):
        parse_page_range("abc")


# ── cache.py: make_task_id ───────────────────────────────────────────────────

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


# ── cache.py: paths ─────────────────────────────────────────────────────────

def test_get_cache_path_ends_with_json():
    assert get_cache_path("test.pdf").endswith(".json")


def test_get_tasks_path_ends_with_tasks_json():
    assert get_tasks_path("test.pdf").endswith("_tasks.json")


def test_different_files_different_paths():
    assert get_cache_path("a.pdf") != get_cache_path("b.pdf")


# ── cache.py: load/save cache (with tmp dir) ────────────────────────────────

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


# ── server.py: _read_image_as_base64 ────────────────────────────────────────

def test_read_image_as_base64(tmp_path):
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    data_uri, mime = _read_image_as_base64(str(img))
    assert data_uri.startswith("data:image/png;base64,")
    assert mime == "image/png"


def test_read_image_as_base64_jpeg(tmp_path):
    img = tmp_path / "photo.jpg"
    img.write_bytes(b"\xff\xd8\xff" + b"\x00" * 100)

    data_uri, mime = _read_image_as_base64(str(img))
    assert "image/jpeg" in data_uri
    assert mime == "image/jpeg"


def test_read_image_as_base64_unknown_ext(tmp_path):
    img = tmp_path / "img.xyz"
    img.write_bytes(b"\x00" * 100)

    _, mime = _read_image_as_base64(str(img))
    assert mime == "image/jpeg"  # default


# ── server.py: _parse_page_content ───────────────────────────────────────────

def test_parse_page_content_text_only():
    blocks = _parse_page_content("Hello world", "/nonexistent", multimodal=True)
    assert len(blocks) == 1
    assert blocks[0] == {"type": "text", "data": "Hello world"}


def test_parse_page_content_no_images():
    blocks = _parse_page_content("Line 1\n\nLine 2", "/nonexistent", multimodal=True)
    assert len(blocks) == 1
    assert "Line 1" in blocks[0]["data"]


def test_parse_page_content_image_not_found(tmp_path):
    text = "Text before ![img](missing.png) text after"
    blocks = _parse_page_content(text, str(tmp_path), multimodal=True)
    assert len(blocks) == 2
    assert blocks[0]["type"] == "text"
    assert "Text before" in blocks[0]["data"]
    assert blocks[1]["type"] == "text"
    assert "text after" in blocks[1]["data"]


def test_parse_page_content_with_image_multimodal(tmp_path):
    img = tmp_path / "photo.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

    text = "Before ![img](photo.png) After"
    blocks = _parse_page_content(text, str(tmp_path), multimodal=True)
    assert len(blocks) == 3
    assert blocks[0]["type"] == "text"
    assert blocks[1]["type"] == "image"
    assert "base64" in blocks[1]
    assert blocks[2]["type"] == "text"


def test_parse_page_content_with_image_ocr(tmp_path):
    img = tmp_path / "chart.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

    text = "See ![img](chart.png) above"
    with patch("carrot_mcp_pdf.server.VISION_MODEL", "test-model"), \
         patch("carrot_mcp_pdf.server.VISION_API_KEY", "fake-key"), \
         patch("carrot_mcp_pdf.server.recognize_image", return_value="OCR text"):
        blocks = _parse_page_content(text, str(tmp_path), multimodal=False)

    assert len(blocks) == 3
    assert blocks[1] == {"type": "text", "data": "OCR text"}


def test_parse_page_content_data_uri_skipped():
    text = "Text ![img](data:image/png;base64,abc) more"
    blocks = _parse_page_content(text, "/nonexistent", multimodal=True)
    assert len(blocks) == 2
    assert blocks[0] == {"type": "text", "data": "Text"}
    assert blocks[1] == {"type": "text", "data": "more"}
    for b in blocks:
        assert "data:image/png" not in b["data"]


def test_parse_page_content_empty_text():
    blocks = _parse_page_content("", "/nonexistent", multimodal=True)
    assert blocks == []


# ── server.py: _get_total_pages ──────────────────────────────────────────────

def test_get_total_pages_from_cache():
    cache = {"total_pages": 42}
    assert _get_total_pages("/fake.pdf", cache) == 42


def test_get_total_pages_zero_no_file(tmp_path):
    cache = {"total_pages": 0}
    result = _get_total_pages(str(tmp_path / "nonexistent.pdf"), cache)
    assert result == 0


# ── server.py: error paths ──────────────────────────────────────────────────

def test_get_toc_file_not_found():
    result = get_toc("nonexistent.pdf")
    assert result["status"] == "error"
    assert "not found" in result["message"].lower()


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

    with patch("carrot_mcp_pdf.server._get_total_pages", return_value=3):
        with patch("carrot_mcp_pdf.server.load_cache", return_value={"pages": {}}):
            result = get_pages(str(pdf), "1-5")

    assert result["status"] == "error"
    assert "out of range" in result["message"].lower()


def test_get_pages_negative_page_range(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"fake pdf")
    result = get_pages(str(pdf), "0")
    assert result["status"] == "error"


def test_create_task_file_not_found():
    result = create_task("nonexistent.pdf")
    assert result["status"] == "error"
    assert "not found" in result["message"].lower()


def test_get_status_not_found():
    result = get_status("nonexistent_task_id")
    assert result["status"] == "error"
    assert "not found" in result["message"].lower()


# ── server.py: create_task with multimodal param ─────────────────────────────

def test_create_task_has_multimodal_param():
    import inspect
    sig = inspect.signature(create_task)
    assert "multimodal" in sig.parameters
    assert sig.parameters["multimodal"].default is True


# ── server.py: get_status returns all fields ─────────────────────────────────

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


# ── ocr.py: recognize_image ─────────────────────────────────────────────────

def _make_mock_litellm(content="ok"):
    mock_litellm = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    mock_litellm.completion.return_value = mock_response
    return mock_litellm


def test_recognize_image_calls_litellm(tmp_path):
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

    mock_litellm = _make_mock_litellm("A chart showing data")
    with patch("carrot_mcp_pdf.ocr.litellm", mock_litellm):
        result = recognize_image(str(img), model="test-model", api_key="test-key")

    assert result == "A chart showing data"
    mock_litellm.completion.assert_called_once()


def test_recognize_image_none_content(tmp_path):
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

    mock_litellm = _make_mock_litellm(content=None)
    with patch("carrot_mcp_pdf.ocr.litellm", mock_litellm):
        result = recognize_image(str(img))

    assert "No response" in result


def test_recognize_image_env_defaults(monkeypatch, tmp_path):
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

    monkeypatch.setenv("CARROT_MCP_MODEL", "env-model")
    monkeypatch.setenv("CARROT_MCP_APIKEY", "env-key")
    monkeypatch.setenv("CARROT_MCP_PROXY", "http://proxy")

    mock_litellm = _make_mock_litellm("ok")
    with patch("carrot_mcp_pdf.ocr.litellm", mock_litellm):
        recognize_image(str(img))

    call_kwargs = mock_litellm.completion.call_args[1]
    assert call_kwargs["model"] == "env-model"
    assert call_kwargs["api_key"] == "env-key"
    assert call_kwargs["proxy"] == "http://proxy"


# ── _resolve_multimodal ─────────────────────────────────────────────────────

def test_resolve_multimodal_no_env():
    with patch("carrot_mcp_pdf.server._MULTIMODAL_ENV", None):
        assert _resolve_multimodal(True) is True
        assert _resolve_multimodal(False) is False


def test_resolve_multimodal_env_true(monkeypatch):
    monkeypatch.setenv("CARROT_MCP_FORCE_MULTIMODAL", "true")
    import carrot_mcp_pdf.server as srv
    srv._MULTIMODAL_ENV = "true"
    assert _resolve_multimodal(False) is True
    srv._MULTIMODAL_ENV = None


def test_resolve_multimodal_env_false(monkeypatch):
    monkeypatch.setenv("CARROT_MCP_FORCE_MULTIMODAL", "false")
    import carrot_mcp_pdf.server as srv
    srv._MULTIMODAL_ENV = "false"
    assert _resolve_multimodal(True) is False
    srv._MULTIMODAL_ENV = None


# ── _vlm_configured ─────────────────────────────────────────────────────────

def test_vlm_configured_both():
    with patch("carrot_mcp_pdf.server.VISION_MODEL", "gpt-4o"), \
         patch("carrot_mcp_pdf.server.VISION_API_KEY", "key"):
        assert _vlm_configured() is True


def test_vlm_configured_no_model():
    with patch("carrot_mcp_pdf.server.VISION_MODEL", None), \
         patch("carrot_mcp_pdf.server.VISION_API_KEY", "key"):
        assert _vlm_configured() is False


def test_vlm_configured_no_key():
    with patch("carrot_mcp_pdf.server.VISION_MODEL", "gpt-4o"), \
         patch("carrot_mcp_pdf.server.VISION_API_KEY", None):
        assert _vlm_configured() is False


def test_vlm_configured_neither():
    with patch("carrot_mcp_pdf.server.VISION_MODEL", None), \
         patch("carrot_mcp_pdf.server.VISION_API_KEY", None):
        assert _vlm_configured() is False


# ── _parse_page_content VLM fallback ────────────────────────────────────────

def test_parse_page_content_vlm_not_configured_fallback(tmp_path):
    img = tmp_path / "chart.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

    text = "See ![img](chart.png) above"
    with patch("carrot_mcp_pdf.server.VISION_MODEL", None), \
         patch("carrot_mcp_pdf.server.VISION_API_KEY", None):
        blocks = _parse_page_content(text, str(tmp_path), multimodal=False)

    assert len(blocks) == 4
    assert blocks[0] == {"type": "text", "data": "See"}
    assert blocks[1]["type"] == "image"
    assert "base64" in blocks[1]
    assert blocks[2] == {"type": "text", "data": "[VLM model not configured, returning image as base64]"}
    assert blocks[3] == {"type": "text", "data": "above"}
