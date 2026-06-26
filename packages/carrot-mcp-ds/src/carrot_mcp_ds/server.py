"""Carrot MCP DS Server"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("carrot-mcp-ds")


@mcp.tool()
def hello(name: str = "World") -> str:
    """Say hello to someone."""
    return f"Hello, {name}! From Carrot MCP DS."


def main():
    mcp.run()


if __name__ == "__main__":
    main()
