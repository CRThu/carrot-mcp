"""Carrot MCP Office Server"""

import sys
from importlib.metadata import version as pkg_version

from carrot_mcp_office._mcp import mcp
from carrot_mcp_office import excel  # noqa: F401
from carrot_mcp_office import word  # noqa: F401


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


def main():
    print("carrot-mcp-office server ready", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
