"""Tests for carrot_mcp_sys.server module."""

from unittest.mock import MagicMock, patch

from carrot_mcp_sys.server import (
    _grab,
    list_monitors,
    mcp,
    screenshot,
    version,
)


# ── version ──────────────────────────────────────────────────────────────────

def test_version():
    result = version()
    assert result["status"] == "ok"
    assert result["name"] == "carrot-mcp-sys"
    assert isinstance(result["version"], str)


# ── MCP server ───────────────────────────────────────────────────────────────

def test_mcp_server_name():
    assert mcp.name == "carrot-mcp-sys"


def test_mcp_tools_registered():
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "version" in tool_names
    assert "list_monitors" in tool_names
    assert "screenshot" in tool_names


# ── list_monitors ────────────────────────────────────────────────────────────

def _mock_monitors():
    """Return a mock monitors list as mss would: [virtual, mon1, mon2]."""
    return [
        {"left": 0, "top": 0, "width": 4480, "height": 1440},
        {"left": 0, "top": 0, "width": 1920, "height": 1080},
        {"left": 1920, "top": 0, "width": 2560, "height": 1440},
    ]


def _mock_mss_instance():
    sct = MagicMock()
    sct.monitors = _mock_monitors()
    return sct


def _mock_sct_cm(mock_sct):
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=mock_sct)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def test_list_monitors_skips_virtual():
    mock_sct = _mock_mss_instance()
    with patch("carrot_mcp_sys.server.mss.mss", return_value=_mock_sct_cm(mock_sct)):
        result = list_monitors()

    assert result["status"] == "ok"
    monitors = result["monitors"]
    assert len(monitors) == 2
    assert monitors[0]["index"] == 1
    assert monitors[0]["left"] == 0
    assert monitors[0]["width"] == 1920
    assert monitors[1]["index"] == 2
    assert monitors[1]["left"] == 1920
    assert monitors[1]["width"] == 2560


def test_list_monitors_single_monitor():
    monitors = [
        {"left": 0, "top": 0, "width": 1920, "height": 1080},
        {"left": 0, "top": 0, "width": 1920, "height": 1080},
    ]
    mock_sct = MagicMock()
    mock_sct.monitors = monitors

    with patch("carrot_mcp_sys.server.mss.mss", return_value=_mock_sct_cm(mock_sct)):
        result = list_monitors()

    assert len(result["monitors"]) == 1
    assert result["monitors"][0]["index"] == 1


# ── screenshot validation ────────────────────────────────────────────────────

def test_screenshot_partial_region():
    result = screenshot(left=10)
    assert result["status"] == "error"
    assert "must all be provided" in result["error"]


def test_screenshot_region_missing_width():
    result = screenshot(left=10, top=20, height=100)
    assert result["status"] == "error"
    assert "must all be provided" in result["error"]


def test_screenshot_zero_width():
    result = screenshot(left=10, top=20, width=0, height=100)
    assert result["status"] == "error"
    assert "positive" in result["error"]


def test_screenshot_negative_height():
    result = screenshot(left=10, top=20, width=100, height=-1)
    assert result["status"] == "error"
    assert "positive" in result["error"]


def test_screenshot_invalid_monitor():
    mock_sct = MagicMock()
    mock_sct.monitors = _mock_monitors()

    with patch("carrot_mcp_sys.server.mss.mss", return_value=_mock_sct_cm(mock_sct)):
        result = screenshot(monitor=5)

    assert result["status"] == "error"
    assert "Invalid monitor" in result["error"]


def test_screenshot_monitor_zero():
    mock_sct = MagicMock()
    mock_sct.monitors = _mock_monitors()

    with patch("carrot_mcp_sys.server.mss.mss", return_value=_mock_sct_cm(mock_sct)):
        result = screenshot(monitor=0)

    assert result["status"] == "error"


# ── screenshot capture ───────────────────────────────────────────────────────

def _mock_grab_result():
    shot = MagicMock()
    shot.size = (1920, 1080)
    shot.rgb = b"\x00" * 100
    return shot


def test_screenshot_single_monitor_auto():
    mock_sct = _mock_mss_instance()
    mock_sct.grab.return_value = _mock_grab_result()

    with patch("carrot_mcp_sys.server.mss.mss", return_value=_mock_sct_cm(mock_sct)):
        result = screenshot()

    assert result["status"] == "ok"
    assert "timestamp" in result
    assert "1" in result["monitors"]


def test_screenshot_specific_monitor():
    mock_sct = _mock_mss_instance()
    mock_sct.grab.return_value = _mock_grab_result()

    with patch("carrot_mcp_sys.server.mss.mss", return_value=_mock_sct_cm(mock_sct)):
        result = screenshot(monitor=2)

    assert result["status"] == "ok"
    assert "2" in result["monitors"]
    monitor_info = result["monitors"]["2"]["monitor"]
    assert monitor_info["index"] == 2
    assert monitor_info["left"] == 1920


def test_screenshot_absolute_region_on_monitor():
    """Region coordinates are absolute — no offset added."""
    mock_sct = _mock_mss_instance()
    shot = _mock_grab_result()
    shot.size = (400, 300)
    mock_sct.grab.return_value = shot

    with patch("carrot_mcp_sys.server.mss.mss", return_value=_mock_sct_cm(mock_sct)):
        result = screenshot(monitor=1, left=100, top=50, width=400, height=300)

    assert result["status"] == "ok"
    monitor_data = result["monitors"]["1"]
    assert monitor_data["width"] == 400
    assert monitor_data["height"] == 300
    assert monitor_data["origin"]["left"] == 100
    assert monitor_data["origin"]["top"] == 50
    region = mock_sct.grab.call_args[0][0]
    assert region["left"] == 100
    assert region["top"] == 50
    assert region["width"] == 400
    assert region["height"] == 300


def test_screenshot_absolute_region_no_monitor():
    """Absolute region without monitor attribution."""
    mock_sct = _mock_mss_instance()
    shot = _mock_grab_result()
    shot.size = (400, 300)
    mock_sct.grab.return_value = shot

    with patch("carrot_mcp_sys.server.mss.mss", return_value=_mock_sct_cm(mock_sct)):
        result = screenshot(left=1920, top=100, width=400, height=300)

    assert result["status"] == "ok"
    assert "0" in result["monitors"]
    region = mock_sct.grab.call_args[0][0]
    assert region["left"] == 1920
    assert region["top"] == 100


def test_screenshot_save_path(tmp_path):
    mock_sct = _mock_mss_instance()
    mock_sct.grab.return_value = _mock_grab_result()

    save_file = str(tmp_path / "sub" / "shot.png")

    with patch("carrot_mcp_sys.server.mss.mss", return_value=_mock_sct_cm(mock_sct)):
        result = screenshot(monitor=1, save_path=save_file)

    assert result["status"] == "ok"
    assert result["monitors"]["1"]["saved_to"] == save_file
    assert (tmp_path / "sub" / "shot.png").exists()


def test_screenshot_timestamp_format():
    mock_sct = _mock_mss_instance()
    mock_sct.grab.return_value = _mock_grab_result()

    with patch("carrot_mcp_sys.server.mss.mss", return_value=_mock_sct_cm(mock_sct)):
        result = screenshot(monitor=1)

    ts = result["timestamp"]
    assert ts.endswith("Z") or "+" in ts
    assert "T" in ts


def test_screenshot_full_monitor_uses_monitor_bounds():
    """When no region, capture uses the monitor's full bounds."""
    mock_sct = _mock_mss_instance()
    mock_sct.grab.return_value = _mock_grab_result()

    with patch("carrot_mcp_sys.server.mss.mss", return_value=_mock_sct_cm(mock_sct)):
        result = screenshot(monitor=2)

    region = mock_sct.grab.call_args[0][0]
    assert region["left"] == 1920
    assert region["top"] == 0
    assert region["width"] == 2560
    assert region["height"] == 1440


# ── _grab ────────────────────────────────────────────────────────────────────

def test_grab_returns_image_block():
    mock_sct = MagicMock()
    shot = _mock_grab_result()
    mock_sct.grab.return_value = shot

    result = _grab(mock_sct, {"left": 0, "top": 0, "width": 100, "height": 100})

    assert result["width"] == 1920
    assert result["height"] == 1080
    assert result["origin"] == {"left": 0, "top": 0}
    assert "bytes" in result
    img = result["image"]
    assert img["type"] == "image"
    assert img["base64"].startswith("data:image/png;base64,")
    assert img["mime"] == "image/png"
