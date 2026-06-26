"""Tests for Carrot MCP NFC Server."""

from carrot_mcp_nfc.server import mcp, hello


def test_hello_default():
    assert hello() == "Hello, World! From Carrot MCP NFC."


def test_hello_custom_name():
    assert hello("Alice") == "Hello, Alice! From Carrot MCP NFC."


def test_mcp_server_name():
    assert mcp.name == "carrot-mcp-nfc"


def test_mcp_tools_registered():
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "hello" in tool_names
