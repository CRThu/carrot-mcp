"""Carrot MCP System Server - screenshot, keyboard, app launcher"""

import base64
import json
import os
from datetime import datetime, timezone
from importlib.metadata import version as pkg_version
from typing import Optional

import mss
import mss.tools
from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent, TextContent

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


def _grab(sct: mss.mss, region: dict, save_path: Optional[str] = None) -> tuple[dict, bytes]:
    shot = sct.grab(region)
    png_data = mss.tools.to_png(shot.rgb, shot.size)

    meta = {
        "width": shot.size[0],
        "height": shot.size[1],
        "origin": {"left": region["left"], "top": region["top"]},
        "bytes": len(png_data),
    }

    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(png_data)
        meta["saved_to"] = save_path

    return meta, png_data


@mcp.tool()
def screenshot(
    monitor: Optional[int] = None,
    left: Optional[int] = None,
    top: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    save_path: Optional[str] = None,
) -> list:
    """Capture a screenshot for multimodal analysis.

    Args:
        monitor: 1-based monitor index. Use `list_monitors` to discover available monitors.
                 If omitted with single-monitor system, auto-selects monitor 1.
        left, top, width, height: Region coordinates in absolute screen pixels.
                                  Must all be provided together. If omitted, captures full monitor.
        save_path: Optional file path to save the PNG image.

    Returns:
        list[TextContent | ImageContent] — first element is JSON metadata (status, timestamp,
        per-monitor dimensions/origin), followed by one ImageContent per captured monitor.
    """
    has_region = any(v is not None for v in (left, top, width, height))
    if has_region and not all(v is not None for v in (left, top, width, height)):
        return [TextContent(type="text", text=json.dumps({"status": "error", "error": "left, top, width, height must all be provided together"}))]
    if has_region and (width is None or height is None or width <= 0 or height <= 0):
        return [TextContent(type="text", text=json.dumps({"status": "error", "error": "Width and height must be positive"}))]

    timestamp = datetime.now(timezone.utc).isoformat()

    with mss.mss() as sct:
        monitors = sct.monitors
        num_monitors = len(monitors) - 1

        if num_monitors == 1 and monitor is None and not has_region:
            monitor = 1

        captures: list[tuple[str, dict, bytes]] = []

        if monitor is not None:
            if monitor < 1 or monitor >= len(monitors):
                return [TextContent(type="text", text=json.dumps({"status": "error", "error": f"Invalid monitor index {monitor}, available: 1-{len(monitors)-1}"}))]
            mon = monitors[monitor]

            if has_region:
                region = {"left": left, "top": top, "width": width, "height": height}
            else:
                region = mon

            meta, png_data = _grab(sct, region, save_path)
            meta["monitor"] = {
                "index": monitor,
                "left": mon["left"],
                "top": mon["top"],
                "width": mon["width"],
                "height": mon["height"],
            }
            captures.append((str(monitor), meta, png_data))

        elif has_region:
            region = {"left": left, "top": top, "width": width, "height": height}
            meta, png_data = _grab(sct, region, save_path)
            captures.append(("0", meta, png_data))

        else:
            for i in range(1, len(monitors)):
                meta, png_data = _grab(sct, monitors[i])
                captures.append((str(i), meta, png_data))

        monitors_dict = {key: meta for key, meta, _ in captures}
        content: list = [
            TextContent(type="text", text=json.dumps({
                "status": "ok",
                "timestamp": timestamp,
                "monitors": monitors_dict,
            })),
        ]
        for key, _, png_data in captures:
            content.append(ImageContent(
                type="image",
                data=base64.b64encode(png_data).decode(),
                mimeType="image/png",
            ))

        return content


def main():
    mcp.run()


if __name__ == "__main__":
    main()
