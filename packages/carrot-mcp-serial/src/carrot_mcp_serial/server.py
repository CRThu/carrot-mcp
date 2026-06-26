"""Carrot MCP Serial Server"""

import sys

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("carrot-mcp-serial")


@mcp.tool()
def hello(name: str = "World") -> str:
    """Say hello."""
    return f"Hello, {name}! From Carrot MCP Serial."


def main():
    print("carrot-mcp-serial server ready", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
