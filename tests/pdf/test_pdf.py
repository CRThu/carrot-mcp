"""Tests for Carrot MCP PDF Server."""

from carrot_mcp_pdf.server import mcp, version, get_toc, get_pages, create_task, get_status


def test_version():
    result = version()
    assert result["status"] == "ok"
    assert result["name"] == "carrot-mcp-pdf"
    assert isinstance(result["version"], str)


def test_mcp_server_name():
    assert mcp.name == "carrot-mcp-pdf"


def test_mcp_tools_registered():
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "version" in tool_names
    assert "get_toc" in tool_names
    assert "get_pages" in tool_names
    assert "create_task" in tool_names
    assert "get_status" in tool_names


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


def test_create_task_file_not_found():
    result = create_task("nonexistent.pdf")
    assert result["status"] == "error"
    assert "not found" in result["message"].lower()


def test_get_status_not_found():
    result = get_status("nonexistent_task_id")
    assert result["status"] == "error"
    assert "not found" in result["message"].lower()
