"""Tests for Carrot MCP NFC Server."""

from unittest.mock import MagicMock

import carrot_mcp_nfc.server as srv
from carrot_mcp_nfc.server import (
    mcp, version, list_readers, connect, disconnect, find,
    transceive, exchange, reqa, wupa, halt, select, anticoll,
    field_on, field_off, script,
    trace_get, trace_clear,
)


def _make_mock_reader(**overrides):
    r = MagicMock()
    r.find.return_value = None
    r.reqa.return_value = None
    r.wupa.return_value = None
    r.halt.return_value = None
    r.select.return_value = None
    r.anticoll.return_value = None
    r.transceive.return_value = None
    r.exchange.return_value = None
    r.last_rx_bits = 0
    r.disconnect.return_value = None
    r.connect.return_value = None
    r.set_crc.return_value = None
    r.set_rf_field.return_value = None
    for k, v in overrides.items():
        setattr(r, k, v) if not callable(v) else setattr(r, k, v)
    return r


def _setup(reader=None):
    srv._reader = reader or _make_mock_reader()
    srv._connected = True


def _teardown():
    srv._reader = None
    srv._connected = False


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
    result = connect(port="COM999")
    assert result["status"] == "error"


def test_connect_already_connected():
    srv._connected = True
    try:
        result = connect(port="COM999")
        assert result["status"] == "ok"
        assert "Already connected" in result["message"]
    finally:
        srv._connected = False


def test_disconnect_not_connected():
    result = disconnect()
    assert result["status"] == "error"


def test_disconnect_success():
    mock_reader = type("MockReader", (), {"disconnect": lambda self: None})()
    srv._reader = mock_reader
    srv._connected = True
    result = disconnect()
    assert result["status"] == "ok"
    assert srv._reader is None
    assert srv._connected is False


def test_find_not_connected():
    result = find()
    assert result["status"] == "error"


def test_find_no_card():
    mock_reader = type("MockReader", (), {"find": lambda self: None})()
    srv._reader = mock_reader
    srv._connected = True
    try:
        result = find()
        assert result["status"] == "error"
        assert "No card found" in result["message"]
    finally:
        srv._connected = False
        srv._reader = None


def test_transceive_not_connected():
    result = transceive(data="6007")
    assert result["status"] == "error"


def test_transceive_invalid_hex():
    srv._connected = True
    srv._reader = object()
    try:
        result = transceive(data="ZZZZ")
        assert result["status"] == "error"
        assert "Invalid hex" in result["message"]
    finally:
        srv._connected = False
        srv._reader = None


def test_exchange_not_connected():
    result = exchange(data="6007")
    assert result["status"] == "error"


def test_exchange_invalid_hex():
    srv._connected = True
    srv._reader = object()
    try:
        result = exchange(data="ZZZZ")
        assert result["status"] == "error"
        assert "Invalid hex" in result["message"]
    finally:
        srv._connected = False
        srv._reader = None


def test_reqa_not_connected():
    result = reqa()
    assert result["status"] == "error"


def test_wupa_not_connected():
    result = wupa()
    assert result["status"] == "error"


def test_halt_not_connected():
    result = halt()
    assert result["status"] == "error"


def test_select_not_connected():
    result = select(cl_level=1, uid="04AABBCCDD77")
    assert result["status"] == "error"


def test_select_invalid_hex():
    srv._connected = True
    srv._reader = object()
    try:
        result = select(cl_level=1, uid="ZZZZ")
        assert result["status"] == "error"
    finally:
        srv._connected = False
        srv._reader = None


def test_anticoll_not_connected():
    result = anticoll(cl_level=1)
    assert result["status"] == "error"


def test_anticoll_invalid_hex():
    srv._connected = True
    srv._reader = object()
    try:
        result = anticoll(cl_level=1, uid_prefix="ZZZZ")
        assert result["status"] == "error"
    finally:
        srv._connected = False
        srv._reader = None


def test_field_on_not_connected():
    result = field_on()
    assert result["status"] == "error"


def test_field_off_not_connected():
    result = field_off()
    assert result["status"] == "error"


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
        "transceive", "exchange", "reqa", "wupa", "halt", "select", "anticoll",
        "field_on", "field_off", "script",
        "trace_get", "trace_clear",
    ]
    for name in expected:
        assert name in tool_names, f"Tool '{name}' not registered"


def test_script_not_connected():
    result = script(steps=[{"op": "reqa"}])
    assert len(result) == 1
    assert result[0]["status"] == "error"
    assert "not connected" in result[0]["message"]


def test_script_unknown_op():
    srv._connected = True
    srv._reader = object()
    try:
        result = script(steps=[{"op": "unknown"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "Unknown op" in result[0]["message"]
    finally:
        srv._connected = False
        srv._reader = None


def test_script_transceive_invalid_hex():
    srv._connected = True
    srv._reader = object()
    try:
        result = script(steps=[{"op": "transceive", "data": "ZZZZ"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "Invalid hex" in result[0]["message"]
    finally:
        srv._connected = False
        srv._reader = None


def test_script_exchange_invalid_hex():
    srv._connected = True
    srv._reader = object()
    try:
        result = script(steps=[{"op": "exchange", "data": "ZZZZ"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "Invalid hex" in result[0]["message"]
    finally:
        srv._connected = False
        srv._reader = None


def test_script_select_invalid_hex():
    srv._connected = True
    srv._reader = object()
    try:
        result = script(steps=[{"op": "select", "cl_level": 1, "uid": "ZZZZ"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "Invalid hex" in result[0]["message"]
    finally:
        srv._connected = False
        srv._reader = None


def test_script_anticoll_invalid_hex():
    srv._connected = True
    srv._reader = object()
    try:
        result = script(steps=[{"op": "anticoll", "uid_prefix": "ZZZZ"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "Invalid hex" in result[0]["message"]
    finally:
        srv._connected = False
        srv._reader = None


def test_script_stops_on_error():
    srv._connected = True
    srv._reader = object()
    try:
        result = script(steps=[
            {"op": "transceive", "data": "ZZZZ"},
            {"op": "reqa"},
        ])
        assert len(result) == 1
        assert result[0]["status"] == "error"
    finally:
        srv._connected = False
        srv._reader = None


def test_script_wait():
    srv._connected = True
    srv._reader = object()
    try:
        result = script(steps=[{"op": "wait", "ms": 10}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["ms"] == 10
    finally:
        srv._connected = False
        srv._reader = None


# --- Connected happy-path tests ---


class MockResponse:
    def __init__(self, data: bytes):
        self.data = data

    def hex(self):
        return self.data.hex()


class MockAnticollResponse(MockResponse):
    def __init__(self, data: bytes, bits: int = 32):
        super().__init__(data)
        self.bits = bits


class MockSelectResponse:
    def __init__(self, data: list[int]):
        self._data = data

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, idx):
        return self._data[idx]

    def hex(self):
        return bytes(self._data).hex()


def test_find_connected_success():
    mock = _make_mock_reader()
    mock.find.return_value = {"uid": b"\x04\xAA\xBB\xCC\xDD", "atq": b"\x00\x44", "sak": 0x08}
    _setup(mock)
    try:
        result = find()
        assert result["status"] == "ok"
        assert result["uid"] == "04AABBCCDD"
        assert result["atq"] == "0044"
        assert result["sak"] == "0x8"
    finally:
        _teardown()


def test_transceive_connected_success():
    mock = _make_mock_reader()
    mock.transceive.return_value = b"\x04\xAA\xBB\xCC\xDD"
    mock.last_rx_bits = 0
    _setup(mock)
    try:
        result = transceive(data="6007")
        assert result["status"] == "ok"
        assert result["data"] == "04AABBCCDD"
        assert result["length"] == 5
        assert result["last_rx_bits"] == 0
        mock.set_crc.assert_called_once_with(True, True)
    finally:
        _teardown()


def test_transceive_no_response():
    mock = _make_mock_reader()
    mock.transceive.return_value = None
    _setup(mock)
    try:
        result = transceive(data="6007")
        assert result["status"] == "error"
        assert "No response" in result["message"]
    finally:
        _teardown()


def test_exchange_connected_success():
    mock = _make_mock_reader()
    mock.exchange.return_value = b"\xAA\xBB"
    _setup(mock)
    try:
        result = exchange(data="6007")
        assert result["status"] == "ok"
        assert result["data"] == "AABB"
        assert result["length"] == 2
    finally:
        _teardown()


def test_exchange_no_response():
    mock = _make_mock_reader()
    mock.exchange.return_value = None
    _setup(mock)
    try:
        result = exchange(data="6007")
        assert result["status"] == "error"
        assert "No response" in result["message"]
    finally:
        _teardown()


def test_reqa_connected_success():
    mock = _make_mock_reader()
    mock.reqa.return_value = MockResponse(b"\x44\x00")
    _setup(mock)
    try:
        result = reqa()
        assert result["status"] == "ok"
        assert result["data"] == "4400"
        assert result["length"] == 2
    finally:
        _teardown()


def test_reqa_no_response():
    mock = _make_mock_reader()
    mock.reqa.return_value = None
    _setup(mock)
    try:
        result = reqa()
        assert result["status"] == "error"
    finally:
        _teardown()


def test_wupa_connected_success():
    mock = _make_mock_reader()
    mock.wupa.return_value = MockResponse(b"\x44\x00")
    _setup(mock)
    try:
        result = wupa()
        assert result["status"] == "ok"
        assert result["data"] == "4400"
    finally:
        _teardown()


def test_halt_connected_success():
    mock = _make_mock_reader()
    mock.halt.return_value = True
    _setup(mock)
    try:
        result = halt()
        assert result["status"] == "ok"
    finally:
        _teardown()


def test_select_connected_success():
    mock = _make_mock_reader()
    mock.select.return_value = MockSelectResponse([0x08, 0x04])
    _setup(mock)
    try:
        result = select(cl_level=1, uid="04AABBCCDD77")
        assert result["status"] == "ok"
        assert result["data"] == "0804"
    finally:
        _teardown()


def test_select_no_response():
    mock = _make_mock_reader()
    mock.select.return_value = None
    _setup(mock)
    try:
        result = select(cl_level=1, uid="04AABBCCDD77")
        assert result["status"] == "error"
    finally:
        _teardown()


def test_anticoll_connected_success():
    mock = _make_mock_reader()
    mock.anticoll.return_value = MockAnticollResponse(b"\x04\xAA\xBB\xCC\xDD", bits=32)
    _setup(mock)
    try:
        result = anticoll(cl_level=1)
        assert result["status"] == "ok"
        assert result["data"] == "04AABBCCDD"
        assert result["bits"] == 32
    finally:
        _teardown()


def test_anticoll_no_response():
    mock = _make_mock_reader()
    mock.anticoll.return_value = None
    _setup(mock)
    try:
        result = anticoll(cl_level=1)
        assert result["status"] == "error"
    finally:
        _teardown()


def test_field_on_connected():
    mock = _make_mock_reader()
    _setup(mock)
    try:
        result = field_on()
        assert result["status"] == "ok"
        mock.set_rf_field.assert_called_once_with(True)
    finally:
        _teardown()


def test_field_off_connected():
    mock = _make_mock_reader()
    _setup(mock)
    try:
        result = field_off()
        assert result["status"] == "ok"
        mock.set_rf_field.assert_called_once_with(False)
    finally:
        _teardown()


def test_disconnect_reader_exception():
    mock = _make_mock_reader()
    mock.disconnect.side_effect = RuntimeError("hw error")
    _setup(mock)
    result = disconnect()
    assert result["status"] == "ok"
    assert srv._reader is None
    assert srv._connected is False


# --- find low_level path ---


def test_find_low_level_no_reqa():
    mock = _make_mock_reader()
    mock.reqa.return_value = None
    _setup(mock)
    try:
        result = find(low_level=True)
        assert result["status"] == "error"
        assert "No card found" in result["message"]
    finally:
        _teardown()


def test_find_low_level_single_cascade():
    mock = _make_mock_reader()
    mock.reqa.return_value = MockResponse(b"\x44\x00")
    mock.anticoll.return_value = MockAnticollResponse(b"\x04\xAA\xBB\xCC\x00", bits=32)
    mock.select.return_value = MockSelectResponse([0x08])
    _setup(mock)
    try:
        result = find(low_level=True)
        assert result["status"] == "ok"
        assert result["uid"] == "04AABBCC"
        assert result["atq"] == "4400"
        assert result["sak"] == "0x8"
        mock.reqa.assert_called_once()
        mock.anticoll.assert_called_once_with(cl_level=1, nvb=0x20)
        mock.select.assert_called_once()
    finally:
        _teardown()


# --- script connected happy-path tests ---


def test_script_reqa_connected():
    mock = _make_mock_reader()
    mock.reqa.return_value = MockResponse(b"\x44\x00")
    _setup(mock)
    try:
        result = script(steps=[{"op": "reqa"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["data"] == "4400"
        assert result[0]["step"] == 0
    finally:
        _teardown()


def test_script_wupa_connected():
    mock = _make_mock_reader()
    mock.wupa.return_value = MockResponse(b"\x44\x00")
    _setup(mock)
    try:
        result = script(steps=[{"op": "wupa"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["data"] == "4400"
    finally:
        _teardown()


def test_script_halt_connected():
    mock = _make_mock_reader()
    mock.halt.return_value = True
    _setup(mock)
    try:
        result = script(steps=[{"op": "halt"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
    finally:
        _teardown()


def test_script_select_connected():
    mock = _make_mock_reader()
    mock.select.return_value = MockSelectResponse([0x08, 0x04])
    _setup(mock)
    try:
        result = script(steps=[{"op": "select", "cl_level": 1, "uid": "04AABBCCDD77"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["data"] == "0804"
    finally:
        _teardown()


def test_script_anticoll_connected():
    mock = _make_mock_reader()
    mock.anticoll.return_value = MockAnticollResponse(b"\x04\xAA\xBB\xCC\xDD", bits=32)
    _setup(mock)
    try:
        result = script(steps=[{"op": "anticoll", "cl_level": 1}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["data"] == "04AABBCCDD"
        assert result[0]["bits"] == 32
    finally:
        _teardown()


def test_script_field_ops_connected():
    mock = _make_mock_reader()
    _setup(mock)
    try:
        result = script(steps=[{"op": "field_on"}, {"op": "field_off"}])
        assert len(result) == 2
        assert all(r["status"] == "ok" for r in result)
        mock.set_rf_field.assert_any_call(True)
        mock.set_rf_field.assert_any_call(False)
    finally:
        _teardown()


def test_script_transceive_connected():
    mock = _make_mock_reader()
    mock.transceive.return_value = b"\x04\xAA"
    mock.last_rx_bits = 8
    _setup(mock)
    try:
        result = script(steps=[{"op": "transceive", "data": "6007"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["data"] == "04AA"
        assert result[0]["last_rx_bits"] == 8
    finally:
        _teardown()


def test_script_exchange_connected():
    mock = _make_mock_reader()
    mock.exchange.return_value = b"\xAA\xBB"
    _setup(mock)
    try:
        result = script(steps=[{"op": "exchange", "data": "6007"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["data"] == "AABB"
    finally:
        _teardown()


def test_script_multi_step_success():
    mock = _make_mock_reader()
    mock.reqa.return_value = MockResponse(b"\x44\x00")
    mock.anticoll.return_value = MockAnticollResponse(b"\x04\xAA\xBB\xCC\xDD", bits=32)
    mock.select.return_value = MockSelectResponse([0x08])
    _setup(mock)
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
        _teardown()


def test_script_stops_on_op_error():
    mock = _make_mock_reader()
    mock.reqa.return_value = None
    mock.halt.return_value = True
    _setup(mock)
    try:
        result = script(steps=[
            {"op": "reqa"},
            {"op": "halt"},
        ])
        assert len(result) == 1
        assert result[0]["status"] == "error"
    finally:
        _teardown()


# --- script expect / on_mismatch ---


def test_script_transceive_expect_match():
    mock = _make_mock_reader()
    mock.transceive.return_value = b"\xAA\xBB"
    mock.last_rx_bits = 0
    _setup(mock)
    try:
        result = script(steps=[{"op": "transceive", "data": "6007", "expect": "AABB"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        _teardown()


def test_script_transceive_expect_mismatch_stop():
    mock = _make_mock_reader()
    mock.transceive.return_value = b"\xAA\xBB"
    mock.last_rx_bits = 0
    _setup(mock)
    try:
        result = script(steps=[{"op": "transceive", "data": "6007", "expect": "CCCC"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert result[0]["matched"] is False
        assert result[0]["expected"] == "CCCC"
    finally:
        _teardown()


def test_script_transceive_expect_mismatch_continue():
    mock = _make_mock_reader()
    mock.transceive.return_value = b"\xAA\xBB"
    mock.reqa.return_value = MockResponse(b"\x44\x00")
    mock.last_rx_bits = 0
    _setup(mock)
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
        _teardown()


def test_script_exchange_expect_match():
    mock = _make_mock_reader()
    mock.exchange.return_value = b"\x01\x02"
    _setup(mock)
    try:
        result = script(steps=[{"op": "exchange", "data": "6007", "expect": "0102"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["matched"] is True
    finally:
        _teardown()


def test_script_exchange_expect_mismatch_stop():
    mock = _make_mock_reader()
    mock.exchange.return_value = b"\x01\x02"
    _setup(mock)
    try:
        result = script(steps=[{"op": "exchange", "data": "6007", "expect": "FFFF"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert result[0]["matched"] is False
    finally:
        _teardown()


def test_script_anticoll_invalid_hex_prefix():
    mock = _make_mock_reader()
    _setup(mock)
    try:
        result = script(steps=[{"op": "anticoll", "uid_prefix": "ZZZZ"}])
        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert "Invalid hex" in result[0]["message"]
    finally:
        _teardown()


# --- find low_level multi-cascade ---


def test_find_low_level_multi_cascade():
    mock = _make_mock_reader()
    mock.reqa.return_value = MockResponse(b"\x44\x00")
    mock.anticoll.side_effect = [
        MockAnticollResponse(b"\x88\x01\x02\x03\x04", bits=32),
        MockAnticollResponse(b"\x04\xAA\xBB\xCC\x00", bits=32),
    ]
    mock.select.return_value = MockSelectResponse([0x08])
    _setup(mock)
    try:
        result = find(low_level=True)
        assert result["status"] == "ok"
        assert result["uid"] == "01020304AABBCC"
        assert result["atq"] == "4400"
        assert result["sak"] == "0x8"
        assert mock.anticoll.call_count == 2
        mock.anticoll.assert_any_call(cl_level=1, nvb=0x20)
        mock.anticoll.assert_any_call(cl_level=2, nvb=0x20)
    finally:
        _teardown()


def test_find_low_level_anticoll_fails():
    mock = _make_mock_reader()
    mock.reqa.return_value = MockResponse(b"\x44\x00")
    mock.anticoll.side_effect = RuntimeError("hw error")
    _setup(mock)
    try:
        result = find(low_level=True)
        assert result["status"] == "error"
    finally:
        _teardown()


def test_find_low_level_select_fails():
    mock = _make_mock_reader()
    mock.reqa.return_value = MockResponse(b"\x44\x00")
    mock.anticoll.return_value = MockAnticollResponse(b"\x04\xAA\xBB\xCC\x00", bits=32)
    mock.select.side_effect = RuntimeError("hw error")
    _setup(mock)
    try:
        result = find(low_level=True)
        assert result["status"] == "error"
    finally:
        _teardown()


# --- connect happy path ---


def test_connect_success():
    from unittest.mock import patch
    mock_reader = _make_mock_reader()
    with patch.object(srv.CardReaderRegistry, "create", return_value=mock_reader):
        result = connect(port="COM20")
        assert result["status"] == "ok"
        assert result["port"] == "COM20"
        assert srv._connected is True
        assert srv._reader is mock_reader
    _teardown()


def test_connect_default_params():
    from unittest.mock import patch
    mock_reader = _make_mock_reader()
    with patch.object(srv.CardReaderRegistry, "create", return_value=mock_reader) as mock_create:
        result = connect(port="COM1")
        assert result["status"] == "ok"
        mock_create.assert_called_once_with("pn532", transport="serial", port="COM1")
    _teardown()


# --- cleanup / shutdown ---


def test_cleanup_not_connected():
    srv._reader = None
    srv._connected = False
    srv._cleanup()
    assert srv._reader is None
    assert srv._connected is False


def test_cleanup_connected():
    mock = _make_mock_reader()
    srv._reader = mock
    srv._connected = True
    srv._cleanup()
    mock.disconnect.assert_called_once()
    assert srv._reader is None
    assert srv._connected is False


def test_cleanup_disconnect_exception():
    mock = _make_mock_reader()
    mock.disconnect.side_effect = RuntimeError("hw error")
    srv._reader = mock
    srv._connected = True
    srv._cleanup()
    assert srv._reader is None
    assert srv._connected is False


def test_shutdown_all():
    mock = _make_mock_reader()
    srv._reader = mock
    srv._connected = True
    srv._shutdown_all()
    mock.disconnect.assert_called_once()
    assert srv._reader is None
    assert srv._connected is False


# --- script anticoll with uid_prefix ---


def test_script_anticoll_with_uid_prefix():
    mock = _make_mock_reader()
    mock.anticoll.return_value = MockAnticollResponse(b"\x04\xAA\xBB\xCC\xDD", bits=32)
    _setup(mock)
    try:
        result = script(steps=[{"op": "anticoll", "cl_level": 2, "uid_prefix": "04AABB"}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        assert result[0]["data"] == "04AABBCCDD"
        mock.anticoll.assert_called_once_with(cl_level=2, nvb=0x20, uid_prefix=[0x04, 0xAA, 0xBB])
    finally:
        _teardown()


def test_script_anticoll_no_uid_prefix():
    mock = _make_mock_reader()
    mock.anticoll.return_value = MockAnticollResponse(b"\x04\xAA\xBB\xCC\xDD", bits=32)
    _setup(mock)
    try:
        result = script(steps=[{"op": "anticoll", "cl_level": 1}])
        assert len(result) == 1
        assert result[0]["status"] == "ok"
        mock.anticoll.assert_called_once_with(cl_level=1, nvb=0x20, uid_prefix=[])
    finally:
        _teardown()
