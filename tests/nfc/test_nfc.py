"""Tests for Carrot MCP NFC Server."""

from unittest.mock import MagicMock, patch

import carrot_mcp_nfc.server as srv
from carrot_mcp_nfc.server import (
    mcp, version, list_readers, connect, disconnect, find,
    transceive, reqa, wupa, halt, select, anticoll,
    field_on, field_off, script,
    trace_get, trace_clear,
)


class MockTransceiveResult:
    def __init__(self, data: bytes, rx_bits: int = 0):
        self.data = data
        self.rx_bits = rx_bits


class MockCardInfo:
    def __init__(self, uid: bytes, atq: bytes, sak: int):
        self.uid = uid
        self.atq = atq
        self.sak = sak


def _patch_nfc(**overrides):
    patches = []
    defaults = {
        "active": MagicMock(return_value=None),
        "transceive_bits": MagicMock(return_value=None),
        "reqa": MagicMock(return_value=None),
        "wupa": MagicMock(return_value=None),
        "halt": MagicMock(return_value=True),
        "select": MagicMock(return_value=None),
        "anticoll": MagicMock(return_value=None),
        "field_on": MagicMock(),
        "field_off": MagicMock(),
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


def test_find_not_connected():
    patches, mocks = _patch_nfc()
    try:
        result = find()
        assert result["status"] == "error"
    finally:
        for p in patches:
            p.stop()


def test_find_no_card():
    patches, mocks = _patch_nfc(active=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = find()
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


def test_select_not_connected():
    patches, mocks = _patch_nfc()
    try:
        result = select(cl_level=1, uid="04AABBCCDD77")
        assert result["status"] == "error"
    finally:
        for p in patches:
            p.stop()


def test_select_invalid_hex():
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = select(cl_level=1, uid="ZZZZ")
        assert result["status"] == "error"
    finally:
        for p in patches:
            p.stop()


def test_anticoll_not_connected():
    patches, mocks = _patch_nfc()
    try:
        result = anticoll(cl_level=1)
        assert result["status"] == "error"
    finally:
        for p in patches:
            p.stop()


def test_anticoll_invalid_hex():
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = anticoll(cl_level=1, uid_prefix="ZZZZ")
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


def test_trace_get_filter_level():
    srv._trace_buffer.clear()
    srv._trace_buffer.append({"time": "00:00:01", "level": "DEBUG", "layer": "DRIVER", "message": "a"})
    srv._trace_buffer.append({"time": "00:00:02", "level": "INFO", "layer": "PROTOCOL", "message": "b"})
    srv._trace_buffer.append({"time": "00:00:03", "level": "DEBUG", "layer": "PROTOCOL", "message": "c"})

    result = trace_get(level="DEBUG")
    assert result["status"] == "ok"
    assert len(result["entries"]) == 2
    assert all(e["level"] == "DEBUG" for e in result["entries"])


def test_trace_get_filter_layer():
    srv._trace_buffer.clear()
    srv._trace_buffer.append({"time": "00:00:01", "level": "DEBUG", "layer": "DRIVER", "message": "a"})
    srv._trace_buffer.append({"time": "00:00:02", "level": "INFO", "layer": "PROTOCOL", "message": "b"})

    result = trace_get(layer="DRIVER")
    assert result["status"] == "ok"
    assert len(result["entries"]) == 1
    assert result["entries"][0]["layer"] == "DRIVER"


def test_trace_get_filter_combined():
    srv._trace_buffer.clear()
    srv._trace_buffer.append({"time": "00:00:01", "level": "DEBUG", "layer": "DRIVER", "message": "a"})
    srv._trace_buffer.append({"time": "00:00:02", "level": "DEBUG", "layer": "PROTOCOL", "message": "b"})
    srv._trace_buffer.append({"time": "00:00:03", "level": "INFO", "layer": "DRIVER", "message": "c"})

    result = trace_get(level="DEBUG", layer="DRIVER")
    assert result["status"] == "ok"
    assert len(result["entries"]) == 1
    assert result["entries"][0]["message"] == "a"


def test_trace_get_filter_no_match():
    srv._trace_buffer.clear()
    srv._trace_buffer.append({"time": "00:00:01", "level": "DEBUG", "layer": "DRIVER", "message": "a"})

    result = trace_get(level="ERROR")
    assert result["status"] == "ok"
    assert len(result["entries"]) == 0


def test_trace_get_case_insensitive():
    srv._trace_buffer.clear()
    srv._trace_buffer.append({"time": "00:00:01", "level": "DEBUG", "layer": "DRIVER", "message": "a"})

    result = trace_get(level="debug")
    assert result["status"] == "ok"
    assert len(result["entries"]) == 1


def test_mcp_server_name():
    assert mcp.name == "carrot-mcp-nfc"


def test_mcp_tools_registered():
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    expected = [
        "version", "list_readers", "connect", "disconnect", "find",
        "transceive", "reqa", "wupa", "halt", "select", "anticoll",
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


def test_script_select_invalid_hex():
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "select", "cl_level": 1, "uid": "ZZZZ"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "Invalid hex" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_anticoll_invalid_hex():
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "anticoll", "uid_prefix": "ZZZZ"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "Invalid hex" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_stops_on_error():
    patches, mocks = _patch_nfc(reqa=MagicMock(return_value=None))
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


def test_find_connected_success():
    card_info = MockCardInfo(uid=b"\x04\xAA\xBB\xCC\xDD", atq=b"\x00\x44", sak=0x08)
    patches, mocks = _patch_nfc(active=MagicMock(return_value=card_info), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = find()
        assert result["status"] == "ok"
        assert result["uid"] == "04AABBCCDD"
        assert result["atq"] == "0044"
        assert result["sak"] == "0x8"
    finally:
        for p in patches:
            p.stop()


def test_transceive_connected_success():
    res = MockTransceiveResult(data=b"\x04\xAA\xBB\xCC\xDD", rx_bits=0)
    mock_reader = MagicMock()
    mock_reader.transceive.return_value = res
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=mock_reader))
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
    mock_reader = MagicMock()
    mock_reader.transceive.return_value = None
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=mock_reader))
    try:
        result = transceive(data="6007")
        assert result["status"] == "error"
        assert "No response" in result["message"]
    finally:
        for p in patches:
            p.stop()


def test_reqa_connected_success():
    res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
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
    patches, mocks = _patch_nfc(reqa=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = reqa()
        assert result["status"] == "error"
    finally:
        for p in patches:
            p.stop()


def test_wupa_connected_success():
    res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
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


def test_select_connected_success():
    patches, mocks = _patch_nfc(select=MagicMock(return_value=[0x08, 0x04]), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = select(cl_level=1, uid="04AABBCCDD77")
        assert result["status"] == "ok"
        assert result["data"] == "0804"
    finally:
        for p in patches:
            p.stop()


def test_select_no_response():
    patches, mocks = _patch_nfc(select=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = select(cl_level=1, uid="04AABBCCDD77")
        assert result["status"] == "error"
    finally:
        for p in patches:
            p.stop()


def test_anticoll_connected_success():
    res = MockTransceiveResult(data=b"\x04\xAA\xBB\xCC\xDD", rx_bits=32)
    patches, mocks = _patch_nfc(anticoll=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = anticoll(cl_level=1)
        assert result["status"] == "ok"
        assert result["data"] == "04AABBCCDD"
        assert result["bits"] == 32
    finally:
        for p in patches:
            p.stop()


def test_anticoll_no_response():
    patches, mocks = _patch_nfc(anticoll=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = anticoll(cl_level=1)
        assert result["status"] == "error"
    finally:
        for p in patches:
            p.stop()


def test_field_on_connected():
    patches, mocks = _patch_nfc(field_on=MagicMock(), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = field_on()
        assert result["status"] == "ok"
        mocks["field_on"].assert_called_once()
    finally:
        for p in patches:
            p.stop()


def test_field_off_connected():
    patches, mocks = _patch_nfc(field_off=MagicMock(), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = field_off()
        assert result["status"] == "ok"
        mocks["field_off"].assert_called_once()
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


# --- find low_level path ---


def test_find_low_level_no_reqa():
    patches, mocks = _patch_nfc(reqa=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = find(low_level=True)
        assert result["status"] == "error"
        assert "No card found" in result["message"]
    finally:
        for p in patches:
            p.stop()


def test_find_low_level_single_cascade():
    reqa_res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
    anticoll_res = MockTransceiveResult(data=b"\x04\xAA\xBB\xCC\x00", rx_bits=32)
    select_res = [0x08]
    patches, mocks = _patch_nfc(
        reqa=MagicMock(return_value=reqa_res),
        anticoll=MagicMock(return_value=anticoll_res),
        select=MagicMock(return_value=select_res),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = find(low_level=True)
        assert result["status"] == "ok"
        assert result["uid"] == "04AABBCC"
        assert result["atq"] == "4400"
        assert result["sak"] == "0x8"
        mocks["reqa"].assert_called_once()
        mocks["anticoll"].assert_called_once_with(cl_level=1, nvb=0x20)
        mocks["select"].assert_called_once()
    finally:
        for p in patches:
            p.stop()


# --- script connected happy-path tests ---


def test_script_reqa_connected():
    res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
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
    res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
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


def test_script_select_connected():
    patches, mocks = _patch_nfc(select=MagicMock(return_value=[0x08, 0x04]), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "select", "cl_level": 1, "uid": "04AABBCCDD77"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["data"] == "0804"
    finally:
        for p in patches:
            p.stop()


def test_script_anticoll_connected():
    res = MockTransceiveResult(data=b"\x04\xAA\xBB\xCC\xDD", rx_bits=32)
    patches, mocks = _patch_nfc(anticoll=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "anticoll", "cl_level": 1}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["data"] == "04AABBCCDD"
        assert result[0]["bits"] == 32
    finally:
        for p in patches:
            p.stop()


def test_script_field_ops_connected():
    patches, mocks = _patch_nfc(field_on=MagicMock(), field_off=MagicMock(), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "field_on"}, {"op": "field_off"}])
        assert len(result) == 2
        assert all(r["status"] == "ok" for r in result)
        mocks["field_on"].assert_called_once()
        mocks["field_off"].assert_called_once()
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_connected():
    res = MockTransceiveResult(data=b"\x04\xAA", rx_bits=8)
    mock_reader = MagicMock()
    mock_reader.transceive.return_value = res
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=mock_reader))
    try:
        result = script(steps=[{"op": "transceive", "data": "6007"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["data"] == "04AA"
        assert result[0]["last_rx_bits"] == 8
    finally:
        for p in patches:
            p.stop()


def test_script_multi_step_success():
    reqa_res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
    anticoll_res = MockTransceiveResult(data=b"\x04\xAA\xBB\xCC\xDD", rx_bits=32)
    select_res = [0x08]
    patches, mocks = _patch_nfc(
        reqa=MagicMock(return_value=reqa_res),
        anticoll=MagicMock(return_value=anticoll_res),
        select=MagicMock(return_value=select_res),
        halt=MagicMock(return_value=True),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[
            {"op": "reqa"},
            {"op": "anticoll", "cl_level": 1},
            {"op": "select", "cl_level": 1, "uid": "04AABBCCDD77"},
            {"op": "halt"},
        ])
        assert len(result) == 4
        assert all(r["status"] == "ok" for r in result)
        for i, r in enumerate(result):
            assert r["step"] == i
    finally:
        for p in patches:
            p.stop()


def test_script_stops_on_op_error():
    patches, mocks = _patch_nfc(reqa=MagicMock(return_value=None), halt=MagicMock(return_value=True))
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
    res = MockTransceiveResult(data=b"\xAA\xBB", rx_bits=0)
    mock_reader = MagicMock()
    mock_reader.transceive.return_value = res
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=mock_reader))
    try:
        result = script(steps=[{"op": "transceive", "data": "6007", "expect": "AABB"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_expect_mismatch_stop():
    res = MockTransceiveResult(data=b"\xAA\xBB", rx_bits=0)
    mock_reader = MagicMock()
    mock_reader.transceive.return_value = res
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=mock_reader))
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
    transceive_res = MockTransceiveResult(data=b"\xAA\xBB", rx_bits=0)
    reqa_res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
    mock_reader = MagicMock()
    mock_reader.transceive.return_value = transceive_res
    patches, mocks = _patch_nfc(
        reqa=MagicMock(return_value=reqa_res),
        get_reader=MagicMock(return_value=mock_reader),
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


def test_script_anticoll_invalid_hex_prefix():
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "anticoll", "uid_prefix": "ZZZZ"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "Invalid hex" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


# --- find low_level multi-cascade ---


def test_find_low_level_multi_cascade():
    reqa_res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
    anticoll_res1 = MockTransceiveResult(data=b"\x88\x01\x02\x03\x04", rx_bits=32)
    anticoll_res2 = MockTransceiveResult(data=b"\x04\xAA\xBB\xCC\x00", rx_bits=32)
    select_res = [0x08]
    patches, mocks = _patch_nfc(
        reqa=MagicMock(return_value=reqa_res),
        anticoll=MagicMock(side_effect=[anticoll_res1, anticoll_res2]),
        select=MagicMock(return_value=select_res),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = find(low_level=True)
        assert result["status"] == "ok"
        assert result["uid"] == "01020304AABBCC"
        assert result["atq"] == "4400"
        assert result["sak"] == "0x8"
        assert mocks["anticoll"].call_count == 2
        mocks["anticoll"].assert_any_call(cl_level=1, nvb=0x20)
        mocks["anticoll"].assert_any_call(cl_level=2, nvb=0x20)
    finally:
        for p in patches:
            p.stop()


def test_find_low_level_anticoll_fails():
    reqa_res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
    patches, mocks = _patch_nfc(
        reqa=MagicMock(return_value=reqa_res),
        anticoll=MagicMock(side_effect=RuntimeError("hw error")),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = find(low_level=True)
        assert result["status"] == "error"
    finally:
        for p in patches:
            p.stop()


def test_find_low_level_select_fails():
    reqa_res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
    anticoll_res = MockTransceiveResult(data=b"\x04\xAA\xBB\xCC\x00", rx_bits=32)
    patches, mocks = _patch_nfc(
        reqa=MagicMock(return_value=reqa_res),
        anticoll=MagicMock(return_value=anticoll_res),
        select=MagicMock(side_effect=RuntimeError("hw error")),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = find(low_level=True)
        assert result["status"] == "error"
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


# --- script anticoll with uid_prefix ---


def test_script_anticoll_with_uid_prefix():
    res = MockTransceiveResult(data=b"\x04\xAA\xBB\xCC\xDD", rx_bits=32)
    patches, mocks = _patch_nfc(anticoll=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "anticoll", "cl_level": 2, "uid_prefix": "04AABB"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["data"] == "04AABBCCDD"
        mocks["anticoll"].assert_called_once_with(cl_level=2, nvb=0x20, uid_prefix=[0x04, 0xAA, 0xBB])
    finally:
        for p in patches:
            p.stop()


def test_script_anticoll_no_uid_prefix():
    res = MockTransceiveResult(data=b"\x04\xAA\xBB\xCC\xDD", rx_bits=32)
    patches, mocks = _patch_nfc(anticoll=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "anticoll", "cl_level": 1}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        mocks["anticoll"].assert_called_once_with(cl_level=1, nvb=0x20, uid_prefix=[])
    finally:
        for p in patches:
            p.stop()


# --- Exception path tests ---


def test_find_exception():
    patches, mocks = _patch_nfc(active=MagicMock(side_effect=RuntimeError("hw error")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = find()
        assert result["status"] == "error"
        assert "hw error" in result["message"]
    finally:
        for p in patches:
            p.stop()


def test_transceive_exception():
    mock_reader = MagicMock()
    mock_reader.transceive.side_effect = RuntimeError("timeout")
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=mock_reader))
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


def test_select_exception():
    patches, mocks = _patch_nfc(select=MagicMock(side_effect=RuntimeError("hw error")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = select(cl_level=1, uid="04AABBCCDD77")
        assert result["status"] == "error"
        assert "hw error" in result["message"]
    finally:
        for p in patches:
            p.stop()


def test_anticoll_exception():
    patches, mocks = _patch_nfc(anticoll=MagicMock(side_effect=RuntimeError("hw error")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = anticoll(cl_level=1)
        assert result["status"] == "error"
        assert "hw error" in result["message"]
    finally:
        for p in patches:
            p.stop()


def test_field_on_exception():
    patches, mocks = _patch_nfc(field_on=MagicMock(side_effect=RuntimeError("hw error")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = field_on()
        assert result["status"] == "error"
        assert "hw error" in result["message"]
    finally:
        for p in patches:
            p.stop()


def test_field_off_exception():
    patches, mocks = _patch_nfc(field_off=MagicMock(side_effect=RuntimeError("hw error")), get_reader=MagicMock(return_value=MagicMock()))
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
    res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=MagicMock()), transceive_bits=MagicMock(return_value=res))
    try:
        result = transceive(data="26", last_tx_bits=7)
        assert result["status"] == "ok"
        assert result["data"] == "4400"
    finally:
        for p in patches:
            p.stop()


def test_transceive_no_response_data_none():
    res = MockTransceiveResult(data=None, rx_bits=0)
    mock_reader = MagicMock()
    mock_reader.transceive.return_value = res
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=mock_reader))
    try:
        result = transceive(data="6007")
        assert result["status"] == "error"
        assert "No response" in result["message"]
    finally:
        for p in patches:
            p.stop()


# --- script parameter passing tests ---


def test_script_transceive_with_last_tx_bits():
    res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
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
    res = MockTransceiveResult(data=b"\xAA\xBB", rx_bits=0)
    mock_reader = MagicMock()
    mock_reader.transceive.return_value = res
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=mock_reader))
    try:
        result = script(steps=[{"op": "transceive", "data": "6007", "tx_crc": False, "rx_crc": False}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        mock_reader.transceive.assert_called_once_with(b'\x60\x07', tx_crc=False, rx_crc=False)
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


def test_script_select_exception():
    patches, mocks = _patch_nfc(select=MagicMock(side_effect=RuntimeError("hw error")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "select", "cl_level": 1, "uid": "04AABBCCDD77"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "hw error" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_anticoll_exception():
    patches, mocks = _patch_nfc(anticoll=MagicMock(side_effect=RuntimeError("hw error")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "anticoll", "cl_level": 1}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "hw error" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_field_on_exception():
    patches, mocks = _patch_nfc(field_on=MagicMock(side_effect=RuntimeError("hw error")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "field_on"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "hw error" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_field_off_exception():
    patches, mocks = _patch_nfc(field_off=MagicMock(side_effect=RuntimeError("hw error")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "field_off"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "hw error" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_find_exception():
    patches, mocks = _patch_nfc(active=MagicMock(side_effect=RuntimeError("hw error")), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "find"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "hw error" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_exception():
    mock_reader = MagicMock()
    mock_reader.transceive.side_effect = RuntimeError("hw error")
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=mock_reader))
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
    patches, mocks = _patch_nfc(wupa=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "wupa"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "No response" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_no_response():
    mock_reader = MagicMock()
    mock_reader.transceive.return_value = None
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=mock_reader))
    try:
        result = script(steps=[{"op": "transceive", "data": "6007"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "No response" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_select_no_response():
    patches, mocks = _patch_nfc(select=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "select", "cl_level": 1, "uid": "04AABBCCDD77"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "No response" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_anticoll_no_response():
    patches, mocks = _patch_nfc(anticoll=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "anticoll", "cl_level": 1}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "No response" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


# --- script find op tests ---


def test_script_find_connected():
    card_info = MockCardInfo(uid=b"\x04\xAA\xBB\xCC\xDD", atq=b"\x00\x44", sak=0x08)
    patches, mocks = _patch_nfc(active=MagicMock(return_value=card_info), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "find"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["uid"] == "04AABBCCDD"
        assert result[0]["atq"] == "0044"
        assert result[0]["sak"] == "0x8"
    finally:
        for p in patches:
            p.stop()


def test_script_find_low_level_connected():
    reqa_res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
    anticoll_res = MockTransceiveResult(data=b"\x04\xAA\xBB\xCC\x00", rx_bits=32)
    select_res = [0x08]
    patches, mocks = _patch_nfc(
        reqa=MagicMock(return_value=reqa_res),
        anticoll=MagicMock(return_value=anticoll_res),
        select=MagicMock(return_value=select_res),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[{"op": "find", "low_level": True}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["uid"] == "04AABBCC"
        assert result[0]["atq"] == "4400"
        assert result[0]["sak"] == "0x8"
    finally:
        for p in patches:
            p.stop()


def test_script_find_no_card():
    patches, mocks = _patch_nfc(active=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "find"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "No card found" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_find_low_level_no_card():
    patches, mocks = _patch_nfc(reqa=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "find", "low_level": True}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "No card found" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_find_stops_script():
    patches, mocks = _patch_nfc(active=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[
            {"op": "find"},
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
    patches, mocks = _patch_nfc(wupa=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
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


# --- script expect/mismatch for reqa, wupa, select, anticoll, find ---


def test_script_reqa_expect_match():
    res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
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
    res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
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
    res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
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
    res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
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
    res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
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
    res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
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


def test_script_select_expect_match():
    patches, mocks = _patch_nfc(select=MagicMock(return_value=[0x08, 0x04]), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "select", "cl_level": 1, "uid": "04AABBCCDD77", "expect": "0804"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_select_expect_mismatch_stop():
    patches, mocks = _patch_nfc(select=MagicMock(return_value=[0x08, 0x04]), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "select", "cl_level": 1, "uid": "04AABBCCDD77", "expect": "FFFF"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert result[0]["matched"] is False
    finally:
        for p in patches:
            p.stop()


def test_script_select_expect_mismatch_continue():
    patches, mocks = _patch_nfc(select=MagicMock(return_value=[0x08, 0x04]), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[
            {"op": "select", "cl_level": 1, "uid": "04AABBCCDD77", "expect": "FFFF", "on_mismatch": "continue"},
            {"op": "halt"},
        ])
        assert len(result) == 2
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is False
        assert result[1]["status"] == "ok"
    finally:
        for p in patches:
            p.stop()


def test_script_anticoll_expect_match():
    res = MockTransceiveResult(data=b"\x04\xAA\xBB\xCC\xDD", rx_bits=32)
    patches, mocks = _patch_nfc(anticoll=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "anticoll", "cl_level": 1, "expect": "04AABBCCDD"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_anticoll_expect_mismatch_stop():
    res = MockTransceiveResult(data=b"\x04\xAA\xBB\xCC\xDD", rx_bits=32)
    patches, mocks = _patch_nfc(anticoll=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "anticoll", "cl_level": 1, "expect": "FFFF"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert result[0]["matched"] is False
    finally:
        for p in patches:
            p.stop()


def test_script_anticoll_expect_mismatch_continue():
    res = MockTransceiveResult(data=b"\x04\xAA\xBB\xCC\xDD", rx_bits=32)
    patches, mocks = _patch_nfc(anticoll=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[
            {"op": "anticoll", "cl_level": 1, "expect": "FFFF", "on_mismatch": "continue"},
            {"op": "halt"},
        ])
        assert len(result) == 2
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is False
        assert result[1]["status"] == "ok"
    finally:
        for p in patches:
            p.stop()


def test_script_find_expect_match():
    card_info = MockCardInfo(uid=b"\x04\xAA\xBB\xCC\xDD", atq=b"\x00\x44", sak=0x08)
    patches, mocks = _patch_nfc(active=MagicMock(return_value=card_info), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "find", "expect": "04AABBCCDD"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_find_expect_mismatch_stop():
    card_info = MockCardInfo(uid=b"\x04\xAA\xBB\xCC\xDD", atq=b"\x00\x44", sak=0x08)
    patches, mocks = _patch_nfc(active=MagicMock(return_value=card_info), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "find", "expect": "FFFF"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert result[0]["matched"] is False
    finally:
        for p in patches:
            p.stop()


def test_script_find_expect_mismatch_continue():
    card_info = MockCardInfo(uid=b"\x04\xAA\xBB\xCC\xDD", atq=b"\x00\x44", sak=0x08)
    patches, mocks = _patch_nfc(active=MagicMock(return_value=card_info), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[
            {"op": "find", "expect": "FFFF", "on_mismatch": "continue"},
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
    res = MockTransceiveResult(data=b"\xAA\xBB", rx_bits=0)
    mock_reader = MagicMock()
    mock_reader.transceive.return_value = res
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=mock_reader))
    try:
        result = script(steps=[{"op": "transceive", "data": "6007", "expect": "aabb"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_multi_step_with_expect():
    reqa_res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
    anticoll_res = MockTransceiveResult(data=b"\x04\xAA\xBB\xCC\xDD", rx_bits=32)
    select_res = [0x08]
    patches, mocks = _patch_nfc(
        reqa=MagicMock(return_value=reqa_res),
        anticoll=MagicMock(return_value=anticoll_res),
        select=MagicMock(return_value=select_res),
        halt=MagicMock(return_value=True),
        get_reader=MagicMock(return_value=MagicMock()),
    )
    try:
        result = script(steps=[
            {"op": "reqa", "expect": "4400"},
            {"op": "anticoll", "cl_level": 1, "expect": "04AABBCCDD"},
            {"op": "select", "cl_level": 1, "uid": "04AABBCCDD77", "expect": "08"},
            {"op": "halt"},
        ])
        assert len(result) == 4
        assert all(r["status"] == "ok" for r in result)
        assert result[0]["matched"] is True
        assert result[1]["matched"] is True
        assert result[2]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_multi_step_expect_stops_on_mismatch():
    reqa_res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
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
    res = MockTransceiveResult(data=b"\x0A", rx_bits=4)
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
    res = MockTransceiveResult(data=b"\xFA", rx_bits=4)
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
    res = MockTransceiveResult(data=b"\x0B", rx_bits=4)
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
    res = MockTransceiveResult(data=b"\xAA\xBB", rx_bits=0)
    mock_reader = MagicMock()
    mock_reader.transceive.return_value = res
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=mock_reader))
    try:
        result = script(steps=[{"op": "transceive", "data": "6007", "expect": "AABB", "expect_bits": 8}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_reqa_expect_bits_match():
    res = MockTransceiveResult(data=b"\x44\x01", rx_bits=0)
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
    patches, mocks = _patch_nfc(reqa=MagicMock(return_value=None), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "reqa"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "No response" in result[0]["message"]
    finally:
        for p in patches:
            p.stop()


def test_script_anticoll_expect_bits_match():
    res = MockTransceiveResult(data=b"\x04\xAA\xBB\xCC\xFF", rx_bits=0)
    patches, mocks = _patch_nfc(anticoll=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "anticoll", "cl_level": 1, "expect": "04AABBCCFF", "expect_bits": 8}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_expect_bits_only_no_expect():
    res = MockTransceiveResult(data=b"\x0A", rx_bits=4)
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
    res = MockTransceiveResult(data=b"\x01", rx_bits=1)
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
    res = MockTransceiveResult(data=b"\x00", rx_bits=1)
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
    res = MockTransceiveResult(data=b"\xAB", rx_bits=8)
    mock_reader = MagicMock()
    mock_reader.transceive.return_value = res
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=mock_reader))
    try:
        result = script(steps=[{"op": "transceive", "data": "6007", "expect": "AB", "expect_bits": 8}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_expect_bits_multi_byte():
    res = MockTransceiveResult(data=b"\xAA\xBB", rx_bits=0)
    mock_reader = MagicMock()
    mock_reader.transceive.return_value = res
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=mock_reader))
    try:
        result = script(steps=[{"op": "transceive", "data": "6007", "expect": "AABB", "expect_bits": 8}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_expect_bits_multi_byte_last_byte_masked():
    res = MockTransceiveResult(data=b"\xAA\xFB", rx_bits=0)
    mock_reader = MagicMock()
    mock_reader.transceive.return_value = res
    patches, mocks = _patch_nfc(get_reader=MagicMock(return_value=mock_reader))
    try:
        result = script(steps=[{"op": "transceive", "data": "6007", "expect": "AA0B", "expect_bits": 4}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_transceive_expect_bits_continue():
    res = MockTransceiveResult(data=b"\x0B", rx_bits=4)
    reqa_res = MockTransceiveResult(data=b"\x44\x00", rx_bits=0)
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


def test_script_find_expect_bits():
    card_info = MockCardInfo(uid=b"\x0A", atq=b"\x00\x44", sak=0x08)
    patches, mocks = _patch_nfc(active=MagicMock(return_value=card_info), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "find", "expect": "0A", "expect_bits": 4}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_reqa_expect_bits():
    res = MockTransceiveResult(data=b"\x44\x01", rx_bits=0)
    patches, mocks = _patch_nfc(reqa=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "reqa", "expect": "4401", "expect_bits": 4}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_select_expect_bits():
    patches, mocks = _patch_nfc(select=MagicMock(return_value=[0x08, 0x04]), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "select", "cl_level": 1, "uid": "04AABBCCDD77", "expect": "0804", "expect_bits": 8}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()


def test_script_anticoll_expect_bits():
    res = MockTransceiveResult(data=b"\x04\xAA\xBB\xCC\xFF", rx_bits=0)
    patches, mocks = _patch_nfc(anticoll=MagicMock(return_value=res), get_reader=MagicMock(return_value=MagicMock()))
    try:
        result = script(steps=[{"op": "anticoll", "cl_level": 1, "expect": "04AABBCC0F", "expect_bits": 4}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        for p in patches:
            p.stop()
