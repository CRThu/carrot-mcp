"""Shared FastMCP instance for carrot-mcp-office."""

from mcp.server.fastmcp import FastMCP

from carrot_mcp_office.backup import save_version

mcp = FastMCP("carrot-mcp-office")


def _save_and_return(path: str, tool: str, result: dict) -> dict:
    """Add version to result and save backup."""
    ver = save_version(path, tool)
    if ver is not None:
        result["version"] = ver
    return result
