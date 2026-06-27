"""Carrot MCP PDF Server"""

import sys
from importlib.metadata import version as pkg_version

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("carrot-mcp-pdf")


@mcp.tool()
def version() -> dict:
    """Get server version info.

    Returns:
        {status, name, version}
    """
    return {
        "status": "ok",
        "name": "carrot-mcp-pdf",
        "version": pkg_version("carrot-mcp-pdf"),
    }


@mcp.tool()
def hello(name: str = "World") -> str:
    """Say hello to someone."""
    return f"Hello, {name}! From Carrot MCP PDF."


def main():
    print("carrot-mcp-pdf server ready", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
