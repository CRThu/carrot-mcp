"""Carrot MCP Office Server"""

import sys
from importlib.metadata import version as pkg_version

from carrot_mcp_office._mcp import mcp
from carrot_mcp_office import excel  # noqa: F401
from carrot_mcp_office import word  # noqa: F401
from carrot_mcp_office.backup import list_versions, restore_version, _backup_root, MAX_VERSIONS, MAX_AGE_DAYS


@mcp.tool()
def version() -> dict:
    """Get server version info and backup configuration.

    Returns:
        {status, name, version, backup}
    """
    return {
        "status": "ok",
        "name": "carrot-mcp-office",
        "version": pkg_version("carrot-mcp-office"),
        "backup": {
            "root": str(_backup_root()),
            "max_versions": MAX_VERSIONS,
            "max_age_days": MAX_AGE_DAYS,
        },
    }


@mcp.tool()
def backup_history(path: str) -> dict:
    """List all backup versions of a file.

    Args:
        path: Absolute path to the original file.
    """
    try:
        versions = list_versions(path)
        return {
            "status": "ok",
            "path": path,
            "versions": [
                {
                    "number": v.number,
                    "file": v.file,
                    "tool": v.tool,
                    "timestamp": v.timestamp,
                    "size": v.original_size,
                }
                for v in versions
            ],
            "count": len(versions),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def backup_restore(path: str, version: int) -> dict:
    """Restore a file to a specific backup version.

    Args:
        path: Absolute path to the original file.
        version: Version number to restore (see backup_history).
    """
    try:
        restore_version(path, version)
        return {"status": "ok", "path": path, "restored_version": version}
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def main():
    print("carrot-mcp-office server ready", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
