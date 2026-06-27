"""Tests for Carrot MCP Office Server."""

from carrot_mcp_office.server import mcp, hello, version


def test_hello_default():
    assert hello() == "Hello, World! From Carrot MCP Office."


def test_hello_custom_name():
    assert hello("Alice") == "Hello, Alice! From Carrot MCP Office."


def test_version():
    result = version()
    assert result["status"] == "ok"
    assert result["name"] == "carrot-mcp-office"
    assert isinstance(result["version"], str)


def test_mcp_server_name():
    assert mcp.name == "carrot-mcp-office"


def test_mcp_tools_registered():
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "hello" in tool_names
    assert "version" in tool_names
