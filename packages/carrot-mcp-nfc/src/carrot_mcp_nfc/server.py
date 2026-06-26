"""Carrot MCP NFC Server"""

import sys
from importlib.metadata import version as pkg_version

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("carrot-mcp-nfc")


@mcp.tool()
def version() -> dict:
    """Get server version info.

    Returns:
        {status, name, version}
    """
    return {
        "status": "ok",
        "name": "carrot-mcp-nfc",
        "version": pkg_version("carrot-mcp-nfc"),
    }


@mcp.tool()
def hello(name: str = "World") -> str:
    """Say hello."""
    return f"Hello, {name}! From Carrot MCP NFC."


def main():
    print("carrot-mcp-nfc server ready", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
