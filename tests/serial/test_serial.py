"""Tests for Carrot MCP Serial Server."""

from carrot_mcp_serial.server import mcp, hello


def test_hello_default():
    assert hello() == "Hello, World! From Carrot MCP Serial."


def test_hello_custom_name():
    assert hello("Alice") == "Hello, Alice! From Carrot MCP Serial."


def test_mcp_server_name():
    assert mcp.name == "carrot-mcp-serial"


def test_mcp_tools_registered():
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "hello" in tool_names
