"""Carrot MCP Office Server"""

import sys
from importlib.metadata import version as pkg_version

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("carrot-mcp-office")


@mcp.tool()
def version() -> dict:
    """Get server version info.

    Returns:
        {status, name, version}
    """
    return {
        "status": "ok",
        "name": "carrot-mcp-office",
        "version": pkg_version("carrot-mcp-office"),
    }


@mcp.tool()
def hello(name: str = "World") -> str:
    """Say hello to someone."""
    return f"Hello, {name}! From Carrot MCP Office."


def main():
    print("carrot-mcp-office server ready", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
