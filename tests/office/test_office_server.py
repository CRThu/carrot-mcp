"""Tests for Office MCP server registration and metadata."""

from carrot_mcp_office.server import mcp, version


def test_version():
    result = version()
    assert result["status"] == "ok"
    assert result["name"] == "carrot-mcp-office"
    assert isinstance(result["version"], str)


def test_mcp_server_name():
    assert mcp.name == "carrot-mcp-office"


def test_mcp_tools_registered():
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    expected = [
        "version",
        "workbook_metadata",
        "workbook_search",
        "create_sheet",
        "rename_sheet",
        "delete_sheet",
        "insert_rows",
        "delete_rows",
        "insert_columns",
        "delete_columns",
        "read_range",
        "write_range",
        "copy_range",
        "delete_range",
        "read_chart",
        "write_chart",
        "format_range",
        "inspect",
        "insert_para",
        "modify_para",
        "format_para",
        "delete_para",
        "insert_table",
        "modify_table",
        "format_table",
        "delete_table",
        "insert_image",
        "delete_image",
        "backup_history",
        "backup_restore",
    ]
    for name in expected:
        assert name in tool_names, f"Tool '{name}' not registered"
