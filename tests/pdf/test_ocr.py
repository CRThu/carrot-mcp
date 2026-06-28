"""Tests for carrot_mcp_pdf.ocr module."""

from unittest.mock import MagicMock, patch

from carrot_mcp_pdf.ocr import recognize_image


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
