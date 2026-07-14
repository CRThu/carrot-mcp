"""Tests for Carrot MCP NFC Server."""

from unittest.mock import MagicMock, patch

import carrot_mcp_nfc.server as srv
from carrot_mcp_nfc.server import (
    mcp, version, list_readers, connect, disconnect, active,
    transceive, reqa, wupa, halt,
    field_on, field_off, script,
    trace_get, trace_clear,
)


class MockTransceiveResult:
    def __init__(self, data: list[int], bits: int = 0):
        self.data = data
        self.bits = bits


class MockCardInfo:
    def __init__(self, uid: list[int], atq: list[int], sak: int):
        self.uid = uid
        self.atq = atq
        self.sak = sak


def _patch_nfc(**overrides):
    patches = []
    defaults = {
        "active": MagicMock(return_value=None),
        "transceive": MagicMock(return_value=None),
        "transceive_bits": MagicMock(return_value=None),
        "reqa": MagicMock(return_value=None),
        "wupa": MagicMock(return_value=None),
        "halt": MagicMock(return_value=True),
        "close": MagicMock(),
        "connect": MagicMock(),
        "get_reader": MagicMock(side_effect=Exception("not connected")),
    }
    defaults.update(overrides)
    for name, mock in defaults.items():
        patches.append(patch(f"carrot_mcp_nfc.server.nfc.{name}", mock))
    for p in patches:
        p.start()
    return patches, defaults


def test_version():
    result = version()
    assert result["status"] == "ok"
    assert result["name"] == "carrot-mcp-nfc"
    assert isinstance(result["version"], str)


def test_list_readers():
    result = list_readers()
    assert result["status"] == "ok"
    assert "readers" in result
    assert "transports" in result
    assert isinstance(result["readers"], list)
    assert isinstance(result["transports"], list)


def test_connect_invalid_port():
    patches, mocks = _patch_nfc(connect=MagicMock(side_effect=Exception("port not found")))
    try:
        result = connect(port="COM999")
        assert result["status"] == "error"
    finally:
        for p in patches:
            p.stop()


def test_connect_already_connected():
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = connect(port="COM999")
        assert result["status"] == "ok"
        assert "Already connected" in result["message"]
    finally:
        for p in patches:
            p.stop()


def test_disconnect_not_connected():
    patches, mocks = _patch_nfc()
    try:
        result = disconnect()
        assert result["status"] == "error"
    finally:
        for p in patches:
            p.stop()


def test_disconnect_success():
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=MagicMock()), close=MagicMock())
    try:
        result = disconnect()
        assert result["status"] == "ok"
        mocks["close"].assert_called_once()
    finally:
        for p in patches:
            p.stop()


def test_active_not_connected():
    patches, mocks = _patch_nfc()
    try:
        result = active()
        assert result["status"] == "error"
    finally:
        for p in patches:
            p.stop()


def test_active_no_card():
    patches, mocks = _patch_nfc(active=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = active()
        assert result["status"] == "error"
        assert "No card found" in result["message"]
    finally:
        for p in patches:
            p.stop()


def test_transceive_not_connected():
    patches, mocks = _patch_nfc()
    try:
        result = transceive(data="6007")
        assert result["status"] == "error"
    finally:
        for p in patches:
            p.stop()


def test_transceive_invalid_hex():
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = transceive(data="ZZZZ")
        assert result["status"] == "error"
        assert "Invalid hex" in result["message"]
    finally:
        for p in patches:
            p.stop()


def test_reqa_not_connected():
    patches, mocks = _patch_nfc()
    try:
        result = reqa()
        assert result["status"] == "error"
    finally:
        for p in patches:
            p.stop()


def test_wupa_not_connected():
    patches, mocks = _patch_nfc()
    try:
        result = wupa()
        assert result["status"] == "error"
    finally:
        for p in patches:
            p.stop()


def test_halt_not_connected():
    patches, mocks = _patch_nfc()
    try:
        result = halt()
        assert result["status"] == "error"
    finally:
        for p in patches:
            p.stop()


def test_field_on_not_connected():
    patches, mocks = _patch_nfc()
    try:
        result = field_on()
        assert result["status"] == "error"
    finally:
        for p in patches:
            p.stop()


def test_field_off_not_connected():
    patches, mocks = _patch_nfc()
    try:
        result = field_off()
        assert result["status"] == "error"
    finally:
        for p in patches:
            p.stop()


def test_trace_get_clear():
    srv._trace_buffer.clear()
    result = trace_get()
    assert result["status"] == "ok"
    assert "entries" in result
    assert isinstance(result["entries"], list)

    result = trace_clear()
    assert result["status"] == "ok"
    assert len(srv._trace_buffer) == 0


def test_trace_get_filter_direction():
    srv._trace_buffer.clear()
    srv._trace_buffer.append({"time": "00:00:01", "layer": "driver", "direction": "TX", "message": "a"})
    srv._trace_buffer.append({"time": "00:00:02", "layer": "protocol", "direction": "RX", "message": "b"})
    srv._trace_buffer.append({"time": "00:00:03", "layer": "protocol", "direction": "TX", "message": "c"})

    result = trace_get(direction="TX")
    assert result["status"] == "ok"
    assert len(result["entries"]) == 2
    assert all(e["direction"] == "TX" for e in result["entries"])


def test_trace_get_filter_layer():
    srv._trace_buffer.clear()
    srv._trace_buffer.append({"time": "00:00:01", "layer": "driver", "direction": "TX", "message": "a"})
    srv._trace_buffer.append({"time": "00:00:02", "layer": "protocol", "direction": "RX", "message": "b"})

    result = trace_get(layer="driver")
    assert result["status"] == "ok"
    assert len(result["entries"]) == 1
    assert result["entries"][0]["layer"] == "driver"


def test_trace_get_filter_combined():
    srv._trace_buffer.clear()
    srv._trace_buffer.append({"time": "00:00:01", "layer": "driver", "direction": "TX", "message": "a"})
    srv._trace_buffer.append({"time": "00:00:02", "layer": "protocol", "direction": "TX", "message": "b"})
    srv._trace_buffer.append({"time": "00:00:03", "layer": "driver", "direction": "RX", "message": "c"})

    result = trace_get(direction="TX", layer="driver")
    assert result["status"] == "ok"
    assert len(result["entries"]) == 1
    assert result["entries"][0]["message"] == "a"


def test_trace_get_filter_no_match():
    srv._trace_buffer.clear()
    srv._trace_buffer.append({"time": "00:00:01", "layer": "driver", "direction": "TX", "message": "a"})

    result = trace_get(direction="INVALID")
    assert result["status"] == "ok"
    assert len(result["entries"]) == 0


def test_trace_get_case_insensitive():
    srv._trace_buffer.clear()
    srv._trace_buffer.append({"time": "00:00:01", "layer": "driver", "direction": "TX", "message": "a"})

    result = trace_get(direction="tx")
    assert result["status"] == "ok"
    assert len(result["entries"]) == 1


def test_mcp_server_name():
    assert mcp.name == "carrot-mcp-nfc"


def test_mcp_tools_registered():
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    expected = [
        "version", "list_readers", "connect", "disconnect", "active",
        "transceive", "reqa", "wupa", "halt",
        "field_on", "field_off", "script",
        "trace_get", "trace_clear",
    ]
    for name in expected:
        assert name in tool_names, f"Tool '{name}' not registered"


def test_script_not_connected():
    patches, mocks = _patch_nfc()
    try:
        result = script(steps=[{"op": "reqa"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "not connected" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_unknown_op():
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "unknown"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "Unknown op" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_invalid_hex():
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "transceive", "data": "ZZZZ"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "Invalid hex" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_stops_on_error():
    patches, mocks = _patch_nfc(reqa=MagicMock(return_value=MockTransceiveResult(data=[], bits=0)))
    try:
        result = script(steps=[
            {"op": "reqa"},
            {"op": "halt"},
        ])
        assert len(result) == 1
        assert result[0]["status"] == "error"
    finally:
        for p in patches:
            p.stop()


def test_script_wait():
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "wait", "ms": 10}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["ms"] == 10
    finally:
        for p in patches:
            p.stop()


# --- Connected happy-path tests ---


def test_active_connected_success():
    card_info = MockCardInfo(uid=[0x04, 0xAA, 0xBB, 0xCC, 0xDD], atq=[0x00, 0x44], sak=0x08)
    patches, mocks = _patch_nfc(active=MagicMock(return_value=card_info), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = active()
        assert result["status"] == "ok"
        assert result["uid"] == "04AABBCCDD"
        assert result["atq"] == "0044"
        assert result["sak"] == "0x8"
    finally:
        for p in patches:
            p.stop()


def test_transceive_connected_success():
    patches, mocks = _patch_nfc(transceive=MagicMock(return_value=[0x04, 0xAA, 0xBB, 0xCC, 0xDD]), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = transceive(data="6007")
        assert result["status"] == "ok"
        assert result["data"] == "04AABBCCDD"
        assert result["length"] == 5
        assert result["last_rx_bits"] == 0
    finally:
        for p in patches:
            p.stop()


def test_transceive_no_response():
    patches, mocks = _patch_nfc(transceive=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = transceive(data="6007")
        assert result["status"] == "error"
        assert "No response" in result["message"]
    finally:
        for p in patches:
            p.stop()


def test_reqa_connected_success():
    res = MockTransceiveResult(data=[0x44, 0x00], bits=0)
    patches, mocks = _patch_nfc(reqa=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = reqa()
        assert result["status"] == "ok"
        assert result["data"] == "4400"
        assert result["length"] == 2
    finally:
        for p in patches:
            p.stop()


def test_reqa_no_response():
    patches, mocks = _patch_nfc(reqa=MagicMock(return_value=MockTransceiveResult(data=[], bits=0)), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = reqa()
        assert result["status"] == "error"
    finally:
        for p in patches:
            p.stop()


def test_wupa_connected_success():
    res = MockTransceiveResult(data=[0x44, 0x00], bits=0)
    patches, mocks = _patch_nfc(wupa=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = wupa()
        assert result["status"] == "ok"
        assert result["data"] == "4400"
    finally:
        for p in patches:
            p.stop()


def test_halt_connected_success():
    patches, mocks = _patch_nfc(halt=MagicMock(return_value=True), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = halt()
        assert result["status"] == "ok"
    finally:
        for p in patches:
            p.stop()


def test_field_on_connected():
    mock_reader = MagicMock()
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=mock_reader))
    try:
        result = field_on()
        assert result["status"] == "ok"
        assert mock_reader.rf_field is True
    finally:
        for p in patches:
            p.stop()


def test_field_off_connected():
    mock_reader = MagicMock()
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=mock_reader))
    try:
        result = field_off()
        assert result["status"] == "ok"
        assert mock_reader.rf_field is False
    finally:
        for p in patches:
            p.stop()


def test_disconnect_reader_exception():
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=MagicMock()), close=MagicMock(side_effect=RuntimeError("hw error")))
    try:
        result = disconnect()
        assert result["status"] == "ok"
    finally:
        for p in patches:
            p.stop()


# --- active low_level path ---


def test_active_low_level_no_reqa():
    patches, mocks = _patch_nfc(active=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = active(low_level=True)
        assert result["status"] == "error"
        assert "No card found" in result["message"]
        mocks["active"].assert_called_once_with(low_layer=True)
    finally:
        for p in patches:
            p.stop()


def test_active_low_level_single_cascade():
    card_info = MockCardInfo(uid=[0x04, 0xAA, 0xBB, 0xCC, 0xDD], atq=[0x44, 0x00], sak=0x08)
    patches, mocks = _patch_nfc(
        active=MagicMock(return_value=card_info),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = active(low_level=True)
        assert result["status"] == "ok"
        assert result["uid"] == "04AABBCCDD"
        assert result["atq"] == "4400"
        assert result["sak"] == "0x8"
        mocks["active"].assert_called_once_with(low_layer=True)
    finally:
        for p in patches:
            p.stop()


# --- script connected happy-path tests ---


def test_script_reqa_connected():
    res = MockTransceiveResult(data=[0x44, 0x00], bits=0)
    patches, mocks = _patch_nfc(reqa=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "reqa"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["data"] == "4400"
        assert result[0]["step"] == 0
    finally:
        for p in patches:
            p.stop()


def test_script_wupa_connected():
    res = MockTransceiveResult(data=[0x44, 0x00], bits=0)
    patches, mocks = _patch_nfc(wupa=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "wupa"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["data"] == "4400"
    finally:
        for p in patches:
            p.stop()


def test_script_halt_connected():
    patches, mocks = _patch_nfc(halt=MagicMock(return_value=True), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "halt"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
    finally:
        for p in patches:
            p.stop()


def test_script_field_ops_connected():
    mock_reader = MagicMock()
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=mock_reader))
    try:
        result = script(steps=[{"op": "field_on"}, {"op": "field_off"}])
        assert len(result) == 2
        assert all(r["status"] == "ok" for r in result)
        assert mock_reader.rf_field is False
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_connected():
    patches, mocks = _patch_nfc(
        transceive=MagicMock(return_value=[0x04, 0xAA]),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[{"op": "transceive", "data": "6007"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["data"] == "04AA"
        assert result[0]["last_rx_bits"] == 0
    finally:
        for p in patches:
            p.stop()


def test_script_multi_step_success():
    reqa_res = MockTransceiveResult(data=[0x44, 0x00], bits=0)
    patches, mocks = _patch_nfc(
        reqa=MagicMock(return_value=reqa_res),
        halt=MagicMock(return_value=True),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[
            {"op": "reqa"},
            {"op": "halt"},
        ])
        assert len(result) == 2
        assert all(r["status"] == "ok" for r in result)
        for i, r in enumerate(result):
            assert r["step"] == i
    finally:
        for p in patches:
            p.stop()


def test_script_stops_on_op_error():
    patches, mocks = _patch_nfc(reqa=MagicMock(return_value=MockTransceiveResult(data=[], bits=0)), halt=MagicMock(return_value=True))
    try:
        result = script(steps=[
            {"op": "reqa"},
            {"op": "halt"},
        ])
        assert len(result) == 1
        assert result[0]["status"] == "error"
    finally:
        for p in patches:
            p.stop()


# --- script expect / on_mismatch ---


def test_script_transceive_expect_match():
    patches, mocks = _patch_nfc(
        transceive=MagicMock(return_value=[0xAA, 0xBB]),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[{"op": "transceive", "data": "6007", "expect": "AABB"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_expect_mismatch_stop():
    patches, mocks = _patch_nfc(
        transceive=MagicMock(return_value=[0xAA, 0xBB]),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[{"op": "transceive", "data": "6007", "expect": "CCCC"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert result[0]["matched"] is False
        assert result[0]["expected"] == "CCCC"
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_expect_mismatch_continue():
    reqa_res = MockTransceiveResult(data=[0x44, 0x00], bits=0)
    patches, mocks = _patch_nfc(
        transceive=MagicMock(return_value=[0xAA, 0xBB]),
        reqa=MagicMock(return_value=reqa_res),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[
            {"op": "transceive", "data": "6007", "expect": "CCCC", "on_mismatch": "continue"},
            {"op": "reqa"},
        ])
        assert len(result) == 2
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is False
        assert result[1]["status"] == "ok"
    finally:
        for p in patches:
            p.stop()


# --- active low_level multi-cascade ---


def test_active_low_level_multi_cascade():
    card_info = MockCardInfo(uid=[0x04, 0xAA, 0xBB, 0xCC, 0xDD], atq=[0x44, 0x00], sak=0x08)
    patches, mocks = _patch_nfc(
        active=MagicMock(return_value=card_info),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = active(low_level=True)
        assert result["status"] == "ok"
        assert result["uid"] == "04AABBCCDD"
        assert result["atq"] == "4400"
        assert result["sak"] == "0x8"
        mocks["active"].assert_called_once_with(low_layer=True)
    finally:
        for p in patches:
            p.stop()


# --- connect happy path ---


def test_connect_success():
    patches, mocks = _patch_nfc(connect=MagicMock())
    try:
        result = connect(port="COM20")
        assert result["status"] == "ok"
        assert result["port"] == "COM20"
        mocks["connect"].assert_called_once_with(port="COM20", reader_type="pn532")
    finally:
        for p in patches:
            p.stop()


def test_connect_default_params():
    patches, mocks = _patch_nfc(connect=MagicMock())
    try:
        result = connect(port="COM1")
        assert result["status"] == "ok"
        mocks["connect"].assert_called_once_with(port="COM1", reader_type="pn532")
    finally:
        for p in patches:
            p.stop()


# --- cleanup / shutdown ---


def test_cleanup_not_connected():
    patches, mocks = _patch_nfc()
    try:
        srv._cleanup()
    finally:
        for p in patches:
            p.stop()


def test_cleanup_connected():
    patches, mocks = _patch_nfc(close=MagicMock(), get_reader=MagicMock(return_value=MagicMock()))
    try:
        srv._cleanup()
        mocks["close"].assert_called_once()
    finally:
        for p in patches:
            p.stop()


def test_cleanup_disconnect_exception():
    patches, mocks = _patch_nfc(close=MagicMock(side_effect=RuntimeError("hw error")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        srv._cleanup()
    finally:
        for p in patches:
            p.stop()


def test_shutdown_all():
    patches, mocks = _patch_nfc(close=MagicMock(), get_reader=MagicMock(return_value=MagicMock()))
    try:
        srv._shutdown_all()
        mocks["close"].assert_called_once()
    finally:
        for p in patches:
            p.stop()


# --- Exception path tests ---


def test_active_exception():
    patches, mocks = _patch_nfc(active=MagicMock(side_effect=RuntimeError("hw error")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = active()
        assert result["status"] == "error"
        assert "hw error" in result["message"]
    finally:
        for p in patches:
            p.stop()


def test_transceive_exception():
    patches, mocks = _patch_nfc(transceive=MagicMock(side_effect=RuntimeError("timeout")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = transceive(data="6007")
        assert result["status"] == "error"
        assert "timeout" in result["message"]
    finally:
        for p in patches:
            p.stop()


def test_reqa_exception():
    patches, mocks = _patch_nfc(reqa=MagicMock(side_effect=RuntimeError("hw error")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = reqa()
        assert result["status"] == "error"
        assert "hw error" in result["message"]
    finally:
        for p in patches:
            p.stop()


def test_wupa_exception():
    patches, mocks = _patch_nfc(wupa=MagicMock(side_effect=RuntimeError("hw error")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = wupa()
        assert result["status"] == "error"
        assert "hw error" in result["message"]
    finally:
        for p in patches:
            p.stop()


def test_halt_exception():
    patches, mocks = _patch_nfc(halt=MagicMock(side_effect=RuntimeError("hw error")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = halt()
        assert result["status"] == "error"
        assert "hw error" in result["message"]
    finally:
        for p in patches:
            p.stop()


def test_field_on_exception():
    class BadReader:
        rf_field = True
        def __setattr__(self, name, value):
            if name == "rf_field":
                raise RuntimeError("hw error")
            super().__setattr__(name, value)
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=BadReader()))
    try:
        result = field_on()
        assert result["status"] == "error"
        assert "hw error" in result["message"]
    finally:
        for p in patches:
            p.stop()


def test_field_off_exception():
    class BadReader:
        rf_field = False
        def __setattr__(self, name, value):
            if name == "rf_field":
                raise RuntimeError("hw error")
            super().__setattr__(name, value)
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=BadReader()))
    try:
        result = field_off()
        assert result["status"] == "error"
        assert "hw error" in result["message"]
    finally:
        for p in patches:
            p.stop()


# --- Parameter validation tests ---


def test_connect_custom_reader_type():
    patches, mocks = _patch_nfc(connect=MagicMock())
    try:
        result = connect(port="COM20", reader_type="clrc663")
        assert result["status"] == "ok"
        mocks["connect"].assert_called_once_with(port="COM20", reader_type="clrc663")
    finally:
        for p in patches:
            p.stop()


# --- transceive parameter tests ---


def test_transceive_with_last_tx_bits():
    res = MockTransceiveResult(data=[0x44, 0x00], bits=0)
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=MagicMock()), transceive_bits=MagicMock(return_value=res))
    try:
        result = transceive(data="26", last_tx_bits=7)
        assert result["status"] == "ok"
        assert result["data"] == "4400"
    finally:
        for p in patches:
            p.stop()


def test_transceive_no_response_data_none():
    patches, mocks = _patch_nfc(transceive=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = transceive(data="6007")
        assert result["status"] == "error"
        assert "No response" in result["message"]
    finally:
        for p in patches:
            p.stop()


# --- script parameter passing tests ---


def test_script_transceive_with_last_tx_bits():
    res = MockTransceiveResult(data=[0x44, 0x00], bits=0)
    patches, mocks = _patch_nfc(
        transceive_bits=MagicMock(return_value=res),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[{"op": "transceive", "data": "26", "last_tx_bits": 7}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        mocks["transceive_bits"].assert_called_once_with([0x26], last_tx_bits=7, tx_crc=True, rx_crc=True)
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_with_crc_params():
    patches, mocks = _patch_nfc(
        transceive=MagicMock(return_value=[0xAA, 0xBB]),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[{"op": "transceive", "data": "6007", "tx_crc": False, "rx_crc": False}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        mocks["transceive"].assert_called_once_with([0x60, 0x07], tx_crc=False, rx_crc=False)
    finally:
        for p in patches:
            p.stop()


# --- script exception tests ---


def test_script_reqa_exception():
    patches, mocks = _patch_nfc(reqa=MagicMock(side_effect=RuntimeError("hw error")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "reqa"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "hw error" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_halt_exception():
    patches, mocks = _patch_nfc(halt=MagicMock(side_effect=RuntimeError("hw error")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "halt"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "hw error" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_wupa_exception():
    patches, mocks = _patch_nfc(wupa=MagicMock(side_effect=RuntimeError("hw error")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "wupa"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "hw error" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_field_on_exception():
    class BadReader:
        rf_field = True
        def __setattr__(self, name, value):
            if name == "rf_field":
                raise RuntimeError("hw error")
            super().__setattr__(name, value)
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=BadReader()))
    try:
        result = script(steps=[{"op": "field_on"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "hw error" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_field_off_exception():
    class BadReader:
        rf_field = False
        def __setattr__(self, name, value):
            if name == "rf_field":
                raise RuntimeError("hw error")
            super().__setattr__(name, value)
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=BadReader()))
    try:
        result = script(steps=[{"op": "field_off"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "hw error" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_active_exception():
    patches, mocks = _patch_nfc(active=MagicMock(side_effect=RuntimeError("hw error")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "active"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "hw error" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_exception():
    patches, mocks = _patch_nfc(
        transceive=MagicMock(side_effect=RuntimeError("hw error")),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[{"op": "transceive", "data": "6007"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "hw error" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


# --- script no-response tests ---


def test_script_wupa_no_response():
    patches, mocks = _patch_nfc(wupa=MagicMock(return_value=MockTransceiveResult(data=[], bits=0)), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "wupa"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "No response" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_no_response():
    patches, mocks = _patch_nfc(transceive=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "transceive", "data": "6007"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "No response" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


# --- script active op tests ---


def test_script_active_connected():
    card_info = MockCardInfo(uid=[0x04, 0xAA, 0xBB, 0xCC, 0xDD], atq=[0x00, 0x44], sak=0x08)
    patches, mocks = _patch_nfc(active=MagicMock(return_value=card_info), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "active"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["uid"] == "04AABBCCDD"
        assert result[0]["atq"] == "0044"
        assert result[0]["sak"] == "0x8"
    finally:
        for p in patches:
            p.stop()


def test_script_active_low_level_connected():
    card_info = MockCardInfo(uid=[0x04, 0xAA, 0xBB, 0xCC, 0xDD], atq=[0x44, 0x00], sak=0x08)
    patches, mocks = _patch_nfc(
        active=MagicMock(return_value=card_info),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[{"op": "active", "low_level": True}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["uid"] == "04AABBCCDD"
        assert result[0]["atq"] == "4400"
        assert result[0]["sak"] == "0x8"
    finally:
        for p in patches:
            p.stop()


def test_script_active_no_card():
    patches, mocks = _patch_nfc(active=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "active"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "No card found" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_active_low_level_no_card():
    patches, mocks = _patch_nfc(active=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "active", "low_level": True}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "No card found" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_active_stops_script():
    patches, mocks = _patch_nfc(active=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[
            {"op": "active"},
            {"op": "halt"},
        ])
        assert len(result) == 1
        assert result[0]["status"] == "error"
    finally:
        for p in patches:
            p.stop()


# --- cleanup exception test ---


def test_cleanup_close_exception():
    patches, mocks = _patch_nfc(close=MagicMock(side_effect=RuntimeError("close error")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        srv._cleanup()
    finally:
        for p in patches:
            p.stop()


# --- non-script method missing tests ---


def test_wupa_no_response():
    patches, mocks = _patch_nfc(wupa=MagicMock(return_value=MockTransceiveResult(data=[], bits=0)), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = wupa()
        assert result["status"] == "error"
        assert "No response" in result["message"]
    finally:
        for p in patches:
            p.stop()


def test_wupa_exception():
    patches, mocks = _patch_nfc(wupa=MagicMock(side_effect=RuntimeError("hw error")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = wupa()
        assert result["status"] == "error"
        assert "hw error" in result["message"]
    finally:
        for p in patches:
            p.stop()


def test_list_readers_exception():
    from nfctester.registry import CardReaderRegistry
    original = CardReaderRegistry.list
    CardReaderRegistry.list = MagicMock(side_effect=RuntimeError("registry error"))
    try:
        result = list_readers()
        assert result["status"] == "error"
        assert "registry error" in result["message"]
    finally:
        CardReaderRegistry.list = original


def test_connect_nfc_exception():
    patches, mocks = _patch_nfc(connect=MagicMock(side_effect=RuntimeError("port busy")))
    try:
        result = connect(port="COM20")
        assert result["status"] == "error"
        assert "port busy" in result["message"]
    finally:
        for p in patches:
            p.stop()


def test_connect_with_transport():
    patches, mocks = _patch_nfc(connect=MagicMock())
    try:
        result = connect(port="COM20", reader_type="clrc663", transport="serial")
        assert result["status"] == "ok"
        assert result["transport"] == "serial"
        mocks["connect"].assert_called_once_with(port="COM20", reader_type="clrc663")
    finally:
        for p in patches:
            p.stop()


# --- script expect/mismatch for reqa, wupa, select, anticoll, active ---


def test_script_reqa_expect_match():
    res = MockTransceiveResult(data=[0x44, 0x00], bits=0)
    patches, mocks = _patch_nfc(reqa=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "reqa", "expect": "4400"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_reqa_expect_mismatch_stop():
    res = MockTransceiveResult(data=[0x44, 0x00], bits=0)
    patches, mocks = _patch_nfc(reqa=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "reqa", "expect": "FFFF"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert result[0]["matched"] is False
        assert result[0]["expected"] == "FFFF"
    finally:
        for p in patches:
            p.stop()


def test_script_reqa_expect_mismatch_continue():
    res = MockTransceiveResult(data=[0x44, 0x00], bits=0)
    patches, mocks = _patch_nfc(reqa=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[
            {"op": "reqa", "expect": "FFFF", "on_mismatch": "continue"},
            {"op": "halt"},
        ])
        assert len(result) == 2
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is False
        assert result[1]["status"] == "ok"
    finally:
        for p in patches:
            p.stop()


def test_script_wupa_expect_match():
    res = MockTransceiveResult(data=[0x44, 0x00], bits=0)
    patches, mocks = _patch_nfc(wupa=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "wupa", "expect": "4400"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_wupa_expect_mismatch_stop():
    res = MockTransceiveResult(data=[0x44, 0x00], bits=0)
    patches, mocks = _patch_nfc(wupa=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "wupa", "expect": "FFFF"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert result[0]["matched"] is False
    finally:
        for p in patches:
            p.stop()


def test_script_wupa_expect_mismatch_continue():
    res = MockTransceiveResult(data=[0x44, 0x00], bits=0)
    patches, mocks = _patch_nfc(wupa=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[
            {"op": "wupa", "expect": "FFFF", "on_mismatch": "continue"},
            {"op": "halt"},
        ])
        assert len(result) == 2
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is False
        assert result[1]["status"] == "ok"
    finally:
        for p in patches:
            p.stop()


def test_script_active_expect_match():
    card_info = MockCardInfo(uid=[0x04, 0xAA, 0xBB, 0xCC, 0xDD], atq=[0x00, 0x44], sak=0x08)
    patches, mocks = _patch_nfc(active=MagicMock(return_value=card_info), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "active", "expect": "04AABBCCDD"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_active_expect_mismatch_stop():
    card_info = MockCardInfo(uid=[0x04, 0xAA, 0xBB, 0xCC, 0xDD], atq=[0x00, 0x44], sak=0x08)
    patches, mocks = _patch_nfc(active=MagicMock(return_value=card_info), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "active", "expect": "FFFF"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert result[0]["matched"] is False
    finally:
        for p in patches:
            p.stop()


def test_script_active_expect_mismatch_continue():
    card_info = MockCardInfo(uid=[0x04, 0xAA, 0xBB, 0xCC, 0xDD], atq=[0x00, 0x44], sak=0x08)
    patches, mocks = _patch_nfc(active=MagicMock(return_value=card_info), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[
            {"op": "active", "expect": "FFFF", "on_mismatch": "continue"},
            {"op": "halt"},
        ])
        assert len(result) == 2
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is False
        assert result[1]["status"] == "ok"
    finally:
        for p in patches:
            p.stop()


def test_script_expect_case_insensitive():
    patches, mocks = _patch_nfc(
        transceive=MagicMock(return_value=[0xAA, 0xBB]),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[{"op": "transceive", "data": "6007", "expect": "aabb"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_multi_step_with_expect():
    reqa_res = MockTransceiveResult(data=[0x44, 0x00], bits=0)
    patches, mocks = _patch_nfc(
        reqa=MagicMock(return_value=reqa_res),
        halt=MagicMock(return_value=True),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[
            {"op": "reqa", "expect": "4400"},
            {"op": "halt"},
        ])
        assert len(result) == 2
        assert all(r["status"] == "ok" for r in result)
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_multi_step_expect_stops_on_mismatch():
    reqa_res = MockTransceiveResult(data=[0x44, 0x00], bits=0)
    patches, mocks = _patch_nfc(
        reqa=MagicMock(return_value=reqa_res),
        halt=MagicMock(return_value=True),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[
            {"op": "reqa", "expect": "4400"},
            {"op": "reqa", "expect": "FFFF"},
            {"op": "halt"},
        ])
        assert len(result) == 2
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
        assert result[1]["status"] == "error"
        assert result[1]["matched"] is False
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_expect_bits_4bit_ack():
    res = MockTransceiveResult(data=[0x0A], bits=4)
    patches, mocks = _patch_nfc(
        transceive_bits=MagicMock(return_value=res),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[{"op": "transceive", "data": "26", "last_tx_bits": 7, "expect": "0A", "expect_bits": 4}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_expect_bits_4bit_upper_nibble_ignored():
    res = MockTransceiveResult(data=[0xFA], bits=4)
    patches, mocks = _patch_nfc(
        transceive_bits=MagicMock(return_value=res),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[{"op": "transceive", "data": "26", "last_tx_bits": 7, "expect": "0A", "expect_bits": 4}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_expect_bits_4bit_mismatch():
    res = MockTransceiveResult(data=[0x0B], bits=4)
    patches, mocks = _patch_nfc(
        transceive_bits=MagicMock(return_value=res),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[{"op": "transceive", "data": "26", "last_tx_bits": 7, "expect": "0A", "expect_bits": 4}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert result[0]["matched"] is False
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_expect_bits_full_byte():
    patches, mocks = _patch_nfc(
        transceive=MagicMock(return_value=[0xAA, 0xBB]),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[{"op": "transceive", "data": "6007", "expect": "AABB", "expect_bits": 8}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_reqa_expect_bits_match():
    res = MockTransceiveResult(data=[0x44, 0x01], bits=0)
    patches, mocks = _patch_nfc(reqa=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "reqa", "expect": "4401", "expect_bits": 8}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_reqa_no_response():
    patches, mocks = _patch_nfc(reqa=MagicMock(return_value=MockTransceiveResult(data=[], bits=0)), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "reqa"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "No response" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_expect_bits_only_no_expect():
    res = MockTransceiveResult(data=[0x0A], bits=4)
    patches, mocks = _patch_nfc(
        transceive_bits=MagicMock(return_value=res),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[{"op": "transceive", "data": "26", "last_tx_bits": 7, "expect_bits": 4}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_expect_bits_1bit():
    res = MockTransceiveResult(data=[0x01], bits=1)
    patches, mocks = _patch_nfc(
        transceive_bits=MagicMock(return_value=res),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[{"op": "transceive", "data": "26", "last_tx_bits": 7, "expect": "01", "expect_bits": 1}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_expect_bits_1bit_mismatch():
    res = MockTransceiveResult(data=[0x00], bits=1)
    patches, mocks = _patch_nfc(
        transceive_bits=MagicMock(return_value=res),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[{"op": "transceive", "data": "26", "last_tx_bits": 7, "expect": "01", "expect_bits": 1}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert result[0]["matched"] is False
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_expect_bits_8bit_full():
    patches, mocks = _patch_nfc(
        transceive=MagicMock(return_value=[0xAB]),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[{"op": "transceive", "data": "6007", "expect": "AB", "expect_bits": 8}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_expect_bits_multi_byte():
    patches, mocks = _patch_nfc(
        transceive=MagicMock(return_value=[0xAA, 0xBB]),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[{"op": "transceive", "data": "6007", "expect": "AABB", "expect_bits": 8}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_expect_bits_multi_byte_last_byte_masked():
    patches, mocks = _patch_nfc(
        transceive=MagicMock(return_value=[0xAA, 0xFB]),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[{"op": "transceive", "data": "6007", "expect": "AA0B", "expect_bits": 4}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_expect_bits_continue():
    res = MockTransceiveResult(data=[0x0B], bits=4)
    reqa_res = MockTransceiveResult(data=[0x44, 0x00], bits=0)
    patches, mocks = _patch_nfc(
        transceive_bits=MagicMock(return_value=res),
        reqa=MagicMock(return_value=reqa_res),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[
            {"op": "transceive", "data": "26", "last_tx_bits": 7, "expect": "0A", "expect_bits": 4, "on_mismatch": "continue"},
            {"op": "reqa"},
        ])
        assert len(result) == 2
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is False
        assert result[1]["status"] == "ok"
    finally:
        for p in patches:
            p.stop()


def test_script_active_expect_bits():
    card_info = MockCardInfo(uid=[0x0A], atq=[0x00, 0x44], sak=0x08)
    patches, mocks = _patch_nfc(active=MagicMock(return_value=card_info), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "active", "expect": "0A", "expect_bits": 4}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_reqa_expect_bits():
    res = MockTransceiveResult(data=[0x44, 0x01], bits=0)
    patches, mocks = _patch_nfc(reqa=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "reqa", "expect": "4401", "expect_bits": 4}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()
