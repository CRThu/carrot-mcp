"""Carrot MCP System Server - screenshot, keyboard, app launcher"""

import base64
import os
from datetime import datetime, timezone
from importlib.metadata import version as pkg_version
from typing import Optional

import mss
import mss.tools
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("carrot-mcp-sys")


@mcp.tool()
def version() -> dict:
    """Get server version info."""
    return {
        "status": "ok",
        "name": "carrot-mcp-sys",
        "version": pkg_version("carrot-mcp-sys"),
    }


@mcp.tool()
def list_monitors() -> dict:
    """List all available monitors with their coordinates and resolution.

    Returns:
        monitors: List of monitors, each with:
            - index: Monitor number (1-based, use for `screenshot(monitor=N)`)
            - left, top: Top-left corner position in screen pixels
            - width, height: Resolution in pixels
    """
    with mss.mss() as sct:
        monitors = []
        for i, mon in enumerate(sct.monitors):
            if i == 0:
                continue
            monitors.append({
                "index": i,
                "left": mon["left"],
                "top": mon["top"],
                "width": mon["width"],
                "height": mon["height"],
            })
    return {"status": "ok", "monitors": monitors}


def _grab(sct: mss.mss, region: dict, save_path: Optional[str] = None) -> dict:
    shot = sct.grab(region)
    png_data = mss.tools.to_png(shot.rgb, shot.size)
    b64 = base64.b64encode(png_data).decode()

    result = {
        "width": shot.size[0],
        "height": shot.size[1],
        "origin": {"left": region["left"], "top": region["top"]},
        "bytes": len(png_data),
        "image": {"type": "image", "base64": f"data:image/png;base64,{b64}", "mime": "image/png"},
    }

    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(png_data)
        result["saved_to"] = save_path

    return result


@mcp.tool()
def screenshot(
    monitor: Optional[int] = None,
    left: Optional[int] = None,
    top: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    save_path: Optional[str] = None,
) -> dict:
    """Capture a screenshot for multimodal analysis.

    ## Coordinate system

    All coordinates are **absolute screen pixels** with origin (0,0) at the
    top-left corner of the virtual screen. Use `list_monitors` to discover
    each monitor's position.

    Typical dual-monitor layout:
        Monitor 1 (left):  left=0,    top=0, width=1920, height=1080
        Monitor 2 (right): left=1920, top=0, width=2560, height=1440

    ## Usage

    - `screenshot()` — capture all monitors (one image per monitor)
    - `screenshot(monitor=1)` — capture full screen of monitor 1
    - `screenshot(left=100, top=50, width=800, height=600)` — capture absolute region
    - `screenshot(monitor=2, left=2000, top=100, width=400, height=300)` — capture absolute region, result attributed to monitor 2

    Args:
        monitor: Monitor index (1-based). Convenience shortcut to capture a full
            monitor without specifying its bounds. Also used to attribute a region
            capture to a specific monitor in the result. When omitted with a
            single-monitor system, automatically uses monitor 1.
        left: X coordinate of the capture region's left edge in absolute screen pixels.
        top: Y coordinate of the capture region's top edge in absolute screen pixels.
        width: Width of the capture region in pixels. Must be positive.
        height: Height of the capture region in pixels. Must be positive.
        save_path: Optional file path to save the PNG image. Ignored when
            capturing all monitors simultaneously.

    Returns:
        status: "ok" or "error"
        timestamp: UTC ISO-8601 timestamp of the capture
        monitors: Dict keyed by monitor index, each containing:
            - width, height: Captured image dimensions
            - origin: The absolute screen position captured {"left": N, "top": N}
            - bytes: PNG file size in bytes
            - image: MCP image block {"type": "image", "base64": "data:image/png;base64,..."}
            - saved_to: File path (when save_path was provided)
    """
    has_region = any(v is not None for v in (left, top, width, height))
    if has_region and not all(v is not None for v in (left, top, width, height)):
        return {"status": "error", "error": "left, top, width, height must all be provided together"}
    if has_region and (width is None or height is None or width <= 0 or height <= 0):
        return {"status": "error", "error": "Width and height must be positive"}

    timestamp = datetime.now(timezone.utc).isoformat()

    with mss.mss() as sct:
        monitors = sct.monitors
        num_monitors = len(monitors) - 1

        if num_monitors == 1 and monitor is None and not has_region:
            monitor = 1

        if monitor is not None:
            if monitor < 1 or monitor >= len(monitors):
                return {"status": "error", "error": f"Invalid monitor index {monitor}, available: 1-{len(monitors)-1}"}
            mon = monitors[monitor]

            if has_region:
                region = {"left": left, "top": top, "width": width, "height": height}
            else:
                region = mon

            shot = _grab(sct, region, save_path)
            shot["monitor"] = {
                "index": monitor,
                "left": mon["left"],
                "top": mon["top"],
                "width": mon["width"],
                "height": mon["height"],
            }
            return {
                "status": "ok",
                "timestamp": timestamp,
                "monitors": {str(monitor): shot},
            }

        if has_region:
            region = {"left": left, "top": top, "width": width, "height": height}
            return {
                "status": "ok",
                "timestamp": timestamp,
                "monitors": {"0": _grab(sct, region, save_path)},
            }

        result_monitors = {}
        for i in range(1, len(monitors)):
            result_monitors[str(i)] = _grab(sct, monitors[i])

        return {
            "status": "ok",
            "timestamp": timestamp,
            "monitors": result_monitors,
        }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
