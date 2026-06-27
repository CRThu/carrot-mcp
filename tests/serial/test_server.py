"""Tests for MCP Serial Server tools."""

import time
from unittest.mock import MagicMock, patch

import serial

from carrot_mcp_serial.channel import Channel
from carrot_mcp_serial.transport import SerialTransport
from carrot_mcp_serial.logger import HistoryLogger
from carrot_mcp_serial.server import (
    _channels,
    _loggers,
    _cleanup_channel,
    _decode,
    _encode,
    _format_result,
    _get_channel,
    _shutdown_all,
    close,
    list_ports,
    open,
    history,
    read,
    recv,
    script,
    version,
    write,
)


def _make_mock_port(is_open=True):
    ser = MagicMock()
    ser.is_open = is_open
    ser.timeout = 1.0
    ser.in_waiting = 0
    ser.out_waiting = 0
    return ser


def _make_mock_channel(port: str, is_open=True):
    ser = _make_mock_port(is_open)
    transport = SerialTransport(ser)
    ch = Channel(transport, rx_maxlen=1024, tx_maxlen=1024)
    logger = HistoryLogger(max_entries=100)
    ch.attach(logger.on_event)
    ch.start()
    _channels[port] = ch
    _loggers[port] = logger
    return ch


def setup_function():
    for ch in _channels.values():
        ch.stop()
    _channels.clear()
    _loggers.clear()


# --- version ---


def test_version():
    result = version()
    assert result["status"] == "ok"
    assert result["name"] == "carrot-mcp-serial"
    assert isinstance(result["version"], str)


# --- _encode / _decode / _format_result ---


def test_encode_hex():
    assert _encode(b"\x48\x65\x6c\x6c\x6f", "hex") == "48656C6C6F"


def test_encode_hex_empty():
    assert _encode(b"", "hex") == ""


def test_encode_ascii_printable():
    assert _encode(b"Hello", "ascii") == "'Hello'"


def test_encode_ascii_newline():
    assert _encode(b"Hello\nWorld", "ascii") == "'Hello\\nWorld'"


def test_encode_ascii_null():
    assert _encode(b"\x00", "ascii") == "'\\x00'"


def test_encode_ascii_mixed():
    assert _encode(b"\x41\x00\x0a", "ascii") == "'A\\x00\\n'"


def test_decode_hex():
    result = _decode("4142", "hex")
    assert result == b"\x41\x42"


def test_decode_ascii():
    result = _decode("AB", "ascii")
    assert result == b"AB"


def test_decode_ascii_newline():
    result = _decode("Hello\\nWorld", "ascii")
    assert result == b"Hello\nWorld"


def test_decode_ascii_hex_escape():
    result = _decode("\\x41\\x42", "ascii")
    assert result == b"AB"


def test_decode_ascii_mixed():
    result = _decode("A\\nB\\x00C", "ascii")
    assert result == b"A\nB\x00C"


def test_decode_ascii_tab():
    result = _decode("a\\tb", "ascii")
    assert result == b"a\tb"


def test_decode_hex_empty():
    result = _decode("", "hex")
    assert result == b""


def test_format_result_hex():
    result = _format_result(b"\x41\x42", "hex")
    assert result == {"length": 2, "data": "4142"}


def test_format_result_ascii():
    result = _format_result(b"AB", "ascii")
    assert result == {"length": 2, "data": "'AB'"}


def test_format_result_empty():
    result = _format_result(b"", "hex")
    assert result == {"length": 0, "data": ""}


# --- _get_channel ---


def test_get_channel_not_exists():
    assert _get_channel("COM99") is None


def test_get_channel_closed():
    _make_mock_channel("COM1", is_open=False)
    assert _get_channel("COM1") is None
    assert "COM1" not in _channels


def test_get_channel_open():
    ch = _make_mock_channel("COM1", is_open=True)
    assert _get_channel("COM1") is ch


# --- list_ports ---


@patch("carrot_mcp_serial.server.serial.tools.list_ports.comports")
def test_list_ports(mock_comports):
    port1 = MagicMock()
    port1.device = "COM3"
    port1.description = "USB Serial"
    port1.hwid = "USB VID:PID=1234:5678"
    mock_comports.return_value = [port1]
    result = list_ports()
    assert len(result) == 1
    assert result[0]["port"] == "COM3"
    assert result[0]["description"] == "USB Serial"


@patch("carrot_mcp_serial.server.serial.tools.list_ports.comports")
def test_list_ports_empty(mock_comports):
    mock_comports.return_value = []
    result = list_ports()
    assert result == []


@patch("carrot_mcp_serial.server.serial.tools.list_ports.comports")
def test_list_ports_error(mock_comports):
    mock_comports.side_effect = Exception("access denied")
    result = list_ports()
    assert isinstance(result, dict)
    assert result["status"] == "error"


# --- open ---


@patch("carrot_mcp_serial.server.serial.Serial")
def test_open_success(mock_serial_cls):
    mock_serial_cls.return_value = _make_mock_port()
    result = open("COM3")
    assert result["status"] == "ok"
    assert result["port"] == "COM3"
    assert result["baudrate"] == 115200
    assert "COM3" in _channels


@patch("carrot_mcp_serial.server.serial.Serial")
def test_open_custom_params(mock_serial_cls):
    mock_serial_cls.return_value = _make_mock_port()
    result = open("COM5", baudrate=9600, parity="E", stopbits=2)
    assert result["status"] == "ok"
    assert result["baudrate"] == 9600
    mock_serial_cls.assert_called_once_with(
        port="COM5", baudrate=9600, bytesize=8,
        parity="E", stopbits=2,
        timeout=1.0, write_timeout=1.0,
    )


@patch("carrot_mcp_serial.server.serial.Serial")
def test_open_write_timeout_propagates_to_channel(mock_serial_cls):
    mock_serial_cls.return_value = _make_mock_port()
    open("COM3", write_timeout=2.5)
    ch = _channels["COM3"]
    assert ch.write_timeout == 2.5


@patch("carrot_mcp_serial.server.serial.Serial")
def test_open_read_timeout_propagates_to_channel(mock_serial_cls):
    mock_serial_cls.return_value = _make_mock_port()
    open("COM3", read_timeout=3.0)
    ch = _channels["COM3"]
    assert ch.read_timeout == 3.0


@patch("carrot_mcp_serial.server.serial.Serial")
def test_open_already_open(mock_serial_cls):
    _make_mock_channel("COM3")
    result = open("COM3")
    assert result["status"] == "ok"
    assert "already open" in result["message"]
    mock_serial_cls.assert_not_called()


@patch("carrot_mcp_serial.server.serial.Serial")
def test_open_exception(mock_serial_cls):
    mock_serial_cls.side_effect = serial.SerialException("port not found")
    result = open("COM99")
    assert result["status"] == "error"
    assert "port not found" in result["message"]
    assert "COM99" not in _channels


@patch("carrot_mcp_serial.server.serial.Serial")
def test_open_attaches_logger(mock_serial_cls):
    mock_serial_cls.return_value = _make_mock_port()
    open("COM3")
    ch = _channels["COM3"]
    assert "COM3" in _loggers
    assert len(ch._observers) == 1


# --- close ---


def test_close_success():
    ch = _make_mock_channel("COM3")
    result = close("COM3")
    assert result["status"] == "ok"
    assert result["port"] == "COM3"
    assert "COM3" not in _channels
    ch._transport._ser.close.assert_called()


def test_close_not_open():
    result = close("COM99")
    assert result["status"] == "error"
    assert "not open" in result["message"]


def test_close_exception_in_close():
    ch = _make_mock_channel("COM3")
    ch._transport._ser.close.side_effect = Exception("close failed")
    result = close("COM3")
    assert result["status"] == "ok"
    assert "COM3" not in _channels


def test_close_removes_logger():
    _make_mock_channel("COM3")
    close("COM3")
    assert "COM3" not in _loggers


# --- read ---


def test_read_success():
    ch = _make_mock_channel("COM3")
    ch._rx.append(b"\x48\x65\x6c\x6c\x6f")
    result = read("COM3", timeout=0)
    assert result["status"] == "ok"
    assert result["data"] == "48656C6C6F"
    assert result["length"] == 5


def test_read_empty():
    _make_mock_channel("COM3")
    result = read("COM3", timeout=0)
    assert result["status"] == "ok"
    assert result["length"] == 0


def test_read_fmt_hex():
    ch = _make_mock_channel("COM3")
    ch._rx.append(b"\x01\x02")
    result = read("COM3", fmt="hex", timeout=0)
    assert result["data"] == "0102"


def test_read_fmt_ascii():
    ch = _make_mock_channel("COM3")
    ch._rx.append(b"AB")
    result = read("COM3", fmt="ascii", timeout=0)
    assert result["data"] == "'AB'"


def test_read_with_timeout_override():
    ch = _make_mock_channel("COM3")
    ch._rx.append(b"\x01")
    result = read("COM3", timeout=0)
    assert result["status"] == "ok"


def test_read_not_open():
    result = read("COM99")
    assert result["status"] == "error"


def test_read_not_open_after_close():
    _make_mock_channel("COM3")
    _channels.pop("COM3")
    result = read("COM3")
    assert result["status"] == "error"
    assert "not open" in result["message"]


# --- recv ---


def test_recv_success():
    ch = _make_mock_channel("COM3")
    ch._rx.append(b"\x01\x02\x03")
    result = recv("COM3")
    assert result["status"] == "ok"
    assert result["data"] == "010203"
    assert result["length"] == 3


def test_recv_empty_buffer():
    _make_mock_channel("COM3")
    result = recv("COM3")
    assert result["status"] == "ok"
    assert result["length"] == 0


def test_recv_with_size():
    ch = _make_mock_channel("COM3")
    ch._rx.append(b"\x01\x02\x03")
    result = recv("COM3", size=2)
    assert result["status"] == "ok"
    assert result["length"] == 2


def test_recv_fmt_hex():
    ch = _make_mock_channel("COM3")
    ch._rx.append(b"\x41\x42")
    result = recv("COM3", fmt="hex")
    assert result["data"] == "4142"


def test_recv_not_open():
    result = recv("COM99")
    assert result["status"] == "error"


def test_recv_not_open_after_close():
    _make_mock_channel("COM3")
    _channels.pop("COM3")
    result = recv("COM3")
    assert result["status"] == "error"
    assert "not open" in result["message"]


# --- write ---


def test_write_hex():
    ch = _make_mock_channel("COM3")
    ch._transport._ser.write.return_value = 5
    result = write("COM3", hex="48656C6C6F")
    assert result["status"] == "ok"
    assert result["bytes_written"] == 5
    ch._transport._ser.write.assert_called_once_with(b"Hello")


def test_write_ascii():
    ch = _make_mock_channel("COM3")
    ch._transport._ser.write.return_value = 5
    result = write("COM3", ascii="Hello")
    assert result["status"] == "ok"
    assert result["bytes_written"] == 5
    ch._transport._ser.write.assert_called_once_with(b"Hello")


def test_write_ascii_with_escape():
    ch = _make_mock_channel("COM3")
    ch._transport._ser.write.return_value = 6
    result = write("COM3", ascii="Hello\\n")
    assert result["status"] == "ok"
    ch._transport._ser.write.assert_called_once_with(b"Hello\n")


def test_write_ascii_hex_escape():
    ch = _make_mock_channel("COM3")
    ch._transport._ser.write.return_value = 1
    result = write("COM3", ascii="\\x41")
    assert result["status"] == "ok"
    ch._transport._ser.write.assert_called_once_with(b"A")


def test_write_both_params():
    _make_mock_channel("COM3")
    result = write("COM3", hex="41", ascii="A")
    assert result["status"] == "error"
    assert "only one" in result["message"]


def test_write_no_params():
    _make_mock_channel("COM3")
    result = write("COM3")
    assert result["status"] == "error"
    assert "Provide" in result["message"]


def test_write_invalid_hex():
    _make_mock_channel("COM3")
    result = write("COM3", hex="ZZZZ")
    assert result["status"] == "error"
    assert "Invalid hex" in result["message"]


def test_write_not_open():
    result = write("COM99", hex="41")
    assert result["status"] == "error"


def test_write_timeout():
    ch = _make_mock_channel("COM3")
    ch._transport._ser.write.side_effect = serial.SerialTimeoutException("timeout")
    result = write("COM3", hex="41")
    assert result["status"] == "error"
    assert "timed out" in result["message"]


def test_write_exception():
    ch = _make_mock_channel("COM3")
    ch._transport._ser.write.side_effect = serial.SerialException("write failed")
    result = write("COM3", hex="41")
    assert result["status"] == "error"
    assert "COM3" not in _channels


# --- script ---


def test_script_write_only():
    ch = _make_mock_channel("COM3")
    ch._transport._ser.write.return_value = 2
    steps = [{"op": "write", "data": "AA BB"}]
    result = script("COM3", steps)
    assert len(result) == 1
    assert result[0]["status"] == "ok"
    assert result[0]["bytes_written"] == 2
    ch._transport._ser.write.assert_called_with(b"\xaa\xbb")


def test_script_wait():
    _make_mock_channel("COM3")
    steps = [{"op": "wait", "ms": 10}]
    result = script("COM3", steps)
    assert len(result) == 1
    assert result[0]["status"] == "ok"
    assert result[0]["ms"] == 10


def test_script_flush():
    ch = _make_mock_channel("COM3")
    steps = [{"op": "flush"}]
    result = script("COM3", steps)
    assert len(result) == 1
    assert result[0]["status"] == "ok"
    ch._transport._ser.reset_input_buffer.assert_called_once()
    ch._transport._ser.reset_output_buffer.assert_called_once()


def test_script_read():
    ch = _make_mock_channel("COM3")
    ch._rx.append(b"\xAA\xBB")
    steps = [{"op": "read", "size": 2, "timeout": 0.5}]
    result = script("COM3", steps)
    assert len(result) == 1
    assert result[0]["status"] == "ok"
    assert result[0]["data"] == "AABB"
    assert result[0]["length"] == 2


def test_script_read_with_match():
    ch = _make_mock_channel("COM3")
    ch._rx.append(b"\xAA\xBB")
    steps = [{"op": "read", "size": 2, "timeout": 0.5, "expect": "AABB"}]
    result = script("COM3", steps)
    assert result[0]["matched"] is True


def test_script_read_no_match():
    ch = _make_mock_channel("COM3")
    ch._rx.append(b"\xAA\xBB")
    steps = [{"op": "read", "size": 2, "timeout": 0.5, "expect": "CCDD"}]
    result = script("COM3", steps)
    assert result[0]["matched"] is False
    assert result[0]["expected"] == "CCDD"
    assert result[0]["status"] == "error"


def test_script_read_mismatch_stops():
    ch = _make_mock_channel("COM3")
    ch._rx.append(b"\xAA\xBB")
    ch._transport._ser.write.return_value = 1
    steps = [
        {"op": "write", "data": "AA"},
        {"op": "read", "size": 2, "timeout": 0.5, "expect": "CCDD", "on_mismatch": "stop"},
        {"op": "wait", "ms": 10},
    ]
    result = script("COM3", steps)
    assert len(result) == 2
    assert result[0]["status"] == "ok"
    assert result[1]["status"] == "error"
    assert result[1]["matched"] is False


def test_script_read_mismatch_continues():
    ch = _make_mock_channel("COM3")
    ch._rx.append(b"\xAA\xBB")
    ch._transport._ser.write.return_value = 1
    steps = [
        {"op": "read", "size": 2, "timeout": 0.5, "expect": "CCDD", "on_mismatch": "continue"},
        {"op": "write", "data": "AA"},
    ]
    result = script("COM3", steps)
    assert len(result) == 2
    assert result[0]["matched"] is False
    assert result[0]["status"] == "ok"
    assert result[1]["status"] == "ok"


def test_script_multi_steps():
    ch = _make_mock_channel("COM3")
    ch._transport._ser.write.return_value = 1
    ch._rx.append(b"\xBB")
    steps = [
        {"op": "write", "data": "AA"},
        {"op": "wait", "ms": 10},
        {"op": "read", "size": 1, "timeout": 1.0},
    ]
    result = script("COM3", steps)
    assert len(result) == 3
    assert result[0]["op"] == "write"
    assert result[1]["op"] == "wait"
    assert result[2]["op"] == "read"
    assert result[2]["data"] == "BB"


def test_script_exception_stops():
    ch = _make_mock_channel("COM3")
    ch._transport._ser.write.side_effect = serial.SerialException("write failed")
    steps = [
        {"op": "write", "data": "AA"},
        {"op": "wait", "ms": 10},
    ]
    result = script("COM3", steps)
    assert len(result) == 1
    assert result[0]["status"] == "error"
    assert "COM3" not in _channels


def test_script_ascii_fmt():
    ch = _make_mock_channel("COM3")
    ch._transport._ser.write.return_value = 5
    steps = [{"op": "write", "data": "Hello"}]
    result = script("COM3", steps, fmt="ascii")
    assert result[0]["status"] == "ok"
    ch._transport._ser.write.assert_called_with(b"Hello")


def test_script_empty_steps():
    _make_mock_channel("COM3")
    result = script("COM3", [])
    assert result == []


def test_script_unknown_op():
    _make_mock_channel("COM3")
    steps = [{"op": "unknown"}]
    result = script("COM3", steps)
    assert result[0]["status"] == "error"
    assert "Unknown op" in result[0]["message"]


# --- history ---


def test_history_success():
    ch = _make_mock_channel("COM3")
    logger = _loggers["COM3"]
    logger.on_event(type('Event', (), {'ts': 0, 'op': 'write', 'data': b'\x01\x02', 'length': 2, 'pending': 0, 'to_dict': lambda self: {'ts': 0, 'op': 'write', 'data': '0102', 'length': 2, 'pending': 0}})())
    logger.on_event(type('Event', (), {'ts': 0, 'op': 'recv', 'data': b'\x03\x04', 'length': 2, 'pending': 0, 'to_dict': lambda self: {'ts': 0, 'op': 'recv', 'data': '0304', 'length': 2, 'pending': 0}})())
    result = history("COM3")
    assert result["status"] == "ok"
    assert len(result["entries"]) == 2
    assert result["entries"][0]["op"] == "write"
    assert result["entries"][1]["op"] == "recv"


def test_history_not_open():
    result = history("COM99")
    assert result["status"] == "error"
    assert "not open" in result["message"]


def test_history_limit():
    ch = _make_mock_channel("COM3")
    logger = _loggers["COM3"]
    for i in range(10):
        logger.on_event(type('Event', (), {'ts': 0, 'op': 'recv', 'data': bytes([i]), 'length': 1, 'pending': 0, 'to_dict': lambda self, i=i: {'ts': 0, 'op': 'recv', 'data': bytes([i]).hex().upper(), 'length': 1, 'pending': 0}})())
    result = history("COM3", limit=5)
    assert result["status"] == "ok"
    assert len(result["entries"]) == 5


# --- _shutdown_all ---


def test_shutdown_all():
    ch1 = _make_mock_channel("COM3")
    ch2 = _make_mock_channel("COM5")
    _shutdown_all()
    assert len(_channels) == 0
    assert len(_loggers) == 0
    ch1._transport._ser.close.assert_called()
    ch2._transport._ser.close.assert_called()


def test_shutdown_all_empty():
    _shutdown_all()  # should not raise


# --- _cleanup_channel ---


def test_cleanup_channel():
    _make_mock_channel("COM3")
    _cleanup_channel("COM3")
    assert "COM3" not in _channels
    assert "COM3" not in _loggers


def test_cleanup_channel_not_exists():
    _cleanup_channel("COM99")  # should not raise
