"""Tests for carrot_mcp_pdf.converter module."""

from unittest.mock import MagicMock, patch

from carrot_mcp_pdf.converter import (
    get_total_pages,
    ocr_page,
    parse_page_content,
    read_image_as_base64,
    render_page_as_image,
    resolve_multimodal,
    vlm_configured,
)


# ── read_image_as_base64 ─────────────────────────────────────────────────────

def test_read_image_as_base64(tmp_path):
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    data_uri, mime = read_image_as_base64(str(img))
    assert data_uri.startswith("data:image/png;base64,")
    assert mime == "image/png"


def test_read_image_as_base64_jpeg(tmp_path):
    img = tmp_path / "photo.jpg"
    img.write_bytes(b"\xff\xd8\xff" + b"\x00" * 100)

    data_uri, mime = read_image_as_base64(str(img))
    assert "image/jpeg" in data_uri
    assert mime == "image/jpeg"


def test_read_image_as_base64_unknown_ext(tmp_path):
    img = tmp_path / "img.xyz"
    img.write_bytes(b"\x00" * 100)

    _, mime = read_image_as_base64(str(img))
    assert mime == "image/jpeg"  # default


# ── parse_page_content ───────────────────────────────────────────────────────

def test_parse_page_content_text_only():
    content, ocr_content = parse_page_content("Hello world", "/nonexistent")
    assert len(content) == 1
    assert content[0] == {"type": "text", "data": "Hello world"}
    assert len(ocr_content) == 1
    assert ocr_content[0] == {"type": "text", "data": "Hello world"}


def test_parse_page_content_no_images():
    content, ocr_content = parse_page_content("Line 1\n\nLine 2", "/nonexistent")
    assert len(content) == 1
    assert "Line 1" in content[0]["data"]
    assert len(ocr_content) == 1
    assert "Line 1" in ocr_content[0]["data"]


def test_parse_page_content_image_not_found(tmp_path):
    text = "Text before ![img](missing.png) text after"
    content, ocr_content = parse_page_content(text, str(tmp_path))
    assert len(content) == 2
    assert content[0]["type"] == "text"
    assert "Text before" in content[0]["data"]
    assert content[1]["type"] == "text"
    assert "text after" in content[1]["data"]
    assert len(ocr_content) == 2


def test_parse_page_content_with_image_multimodal(tmp_path):
    img = tmp_path / "photo.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

    text = "Before ![img](photo.png) After"
    content, ocr_content = parse_page_content(text, str(tmp_path))
    assert len(content) == 3
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image"
    assert "base64" in content[1]
    assert content[2]["type"] == "text"


def test_parse_page_content_with_image_ocr(tmp_path):
    img = tmp_path / "chart.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

    text = "See ![img](chart.png) above"
    with patch("carrot_mcp_pdf.converter.VISION_MODEL", "test-model"), \
         patch("carrot_mcp_pdf.converter.VISION_API_KEY", "fake-key"), \
         patch("carrot_mcp_pdf.converter.recognize_image", return_value="OCR text"):
        content, ocr_content = parse_page_content(text, str(tmp_path))

    assert len(content) == 3
    assert content[1]["type"] == "image"
    assert len(ocr_content) == 3
    assert ocr_content[1] == {"type": "text", "data": "OCR text"}


def test_parse_page_content_data_uri_skipped():
    text = "Text ![img](data:image/png;base64,abc) more"
    content, ocr_content = parse_page_content(text, "/nonexistent")
    assert len(content) == 2
    assert content[0] == {"type": "text", "data": "Text"}
    assert content[1] == {"type": "text", "data": "more"}
    for b in content:
        assert "data:image/png" not in b.get("data", "")


def test_parse_page_content_empty_text():
    content, ocr_content = parse_page_content("", "/nonexistent")
    assert content == []
    assert ocr_content == []


def test_parse_page_content_vlm_not_configured_fallback(tmp_path):
    img = tmp_path / "chart.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

    text = "See ![img](chart.png) above"
    with patch("carrot_mcp_pdf.converter.VISION_MODEL", None), \
         patch("carrot_mcp_pdf.converter.VISION_API_KEY", None):
        content, ocr_content = parse_page_content(text, str(tmp_path))

    assert len(content) == 3
    assert content[0] == {"type": "text", "data": "See"}
    assert content[1]["type"] == "image"
    assert "base64" in content[1]
    assert content[2] == {"type": "text", "data": "above"}

    assert len(ocr_content) == 4
    assert ocr_content[0] == {"type": "text", "data": "See"}
    assert ocr_content[1]["type"] == "image"
    assert "base64" in ocr_content[1]
    assert ocr_content[2] == {"type": "text", "data": "[VLM model not configured, returning image as base64]"}
    assert ocr_content[3] == {"type": "text", "data": "above"}


# ── get_total_pages ──────────────────────────────────────────────────────────

def test_get_total_pages_from_cache():
    cache = {"total_pages": 42}
    assert get_total_pages("/fake.pdf", cache) == 42


def test_get_total_pages_zero_no_file(tmp_path):
    cache = {"total_pages": 0}
    result = get_total_pages(str(tmp_path / "nonexistent.pdf"), cache)
    assert result == 0


# ── resolve_multimodal ───────────────────────────────────────────────────────

def test_resolve_multimodal_no_env():
    with patch("carrot_mcp_pdf.converter._MULTIMODAL_ENV", None):
        assert resolve_multimodal(True) is True
        assert resolve_multimodal(False) is False


def test_resolve_multimodal_env_true(monkeypatch):
    monkeypatch.setenv("CARROT_MCP_FORCE_MULTIMODAL", "true")
    import carrot_mcp_pdf.converter as conv
    conv._MULTIMODAL_ENV = "true"
    assert resolve_multimodal(False) is True
    conv._MULTIMODAL_ENV = None


def test_resolve_multimodal_env_false(monkeypatch):
    monkeypatch.setenv("CARROT_MCP_FORCE_MULTIMODAL", "false")
    import carrot_mcp_pdf.converter as conv
    conv._MULTIMODAL_ENV = "false"
    assert resolve_multimodal(True) is False
    conv._MULTIMODAL_ENV = None


# ── vlm_configured ───────────────────────────────────────────────────────────

def test_vlm_configured_both():
    with patch("carrot_mcp_pdf.converter.VISION_MODEL", "gpt-4o"), \
         patch("carrot_mcp_pdf.converter.VISION_API_KEY", "key"):
        assert vlm_configured() is True


def test_vlm_configured_no_model():
    with patch("carrot_mcp_pdf.converter.VISION_MODEL", None), \
         patch("carrot_mcp_pdf.converter.VISION_API_KEY", "key"):
        assert vlm_configured() is False


def test_vlm_configured_no_key():
    with patch("carrot_mcp_pdf.converter.VISION_MODEL", "gpt-4o"), \
         patch("carrot_mcp_pdf.converter.VISION_API_KEY", None):
        assert vlm_configured() is False


def test_vlm_configured_neither():
    with patch("carrot_mcp_pdf.converter.VISION_MODEL", None), \
         patch("carrot_mcp_pdf.converter.VISION_API_KEY", None):
        assert vlm_configured() is False


# ── ocr_page ─────────────────────────────────────────────────────────────────

def test_ocr_page_vlm_not_configured():
    with patch("carrot_mcp_pdf.converter.VISION_MODEL", None), \
         patch("carrot_mcp_pdf.converter.VISION_API_KEY", None):
        result = ocr_page("/fake.pdf", 1)
    assert len(result) == 1
    assert result[0]["type"] == "text"
    assert "not configured" in result[0]["data"].lower()


def test_ocr_page_success(tmp_path):
    img = tmp_path / "page.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

    with patch("carrot_mcp_pdf.converter.VISION_MODEL", "test-model"), \
         patch("carrot_mcp_pdf.converter.VISION_API_KEY", "fake-key"), \
         patch("carrot_mcp_pdf.converter.render_page_as_image", return_value=str(img)), \
         patch("carrot_mcp_pdf.converter.recognize_image", return_value="OCR result"):
        result = ocr_page("/fake.pdf", 1)

    assert len(result) == 1
    assert result[0] == {"type": "text", "data": "OCR result"}


def test_ocr_page_cleanup_on_success(tmp_path):
    img = tmp_path / "page.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

    with patch("carrot_mcp_pdf.converter.VISION_MODEL", "test-model"), \
         patch("carrot_mcp_pdf.converter.VISION_API_KEY", "fake-key"), \
         patch("carrot_mcp_pdf.converter.render_page_as_image", return_value=str(img)), \
         patch("carrot_mcp_pdf.converter.recognize_image", return_value="ok"):
        ocr_page("/fake.pdf", 1)

    assert not img.exists()


def test_ocr_page_cleanup_on_error(tmp_path):
    img = tmp_path / "page.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

    with patch("carrot_mcp_pdf.converter.VISION_MODEL", "test-model"), \
         patch("carrot_mcp_pdf.converter.VISION_API_KEY", "fake-key"), \
         patch("carrot_mcp_pdf.converter.render_page_as_image", return_value=str(img)), \
         patch("carrot_mcp_pdf.converter.recognize_image", side_effect=RuntimeError("API error")):
        try:
            ocr_page("/fake.pdf", 1)
        except RuntimeError:
            pass

    assert not img.exists()


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

        with patch("builtins.open", MagicMock()):
            with patch("tempfile.NamedTemporaryFile") as mock_tmp:
                mock_tmp.return_value.__enter__ = MagicMock(return_value=mock_tmp)
                mock_tmp.return_value.__exit__ = MagicMock(return_value=False)
                mock_tmp.return_value.name = "/tmp/test.png"
                result = render_page_as_image("/fake.pdf", 1)

    assert result == "/tmp/test.png"
