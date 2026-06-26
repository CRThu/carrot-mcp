"""Tests for Carrot MCP Serial Server."""

from unittest.mock import MagicMock, patch

import serial

from carrot_mcp_serial.server import (
    _decode,
    _encode,
    _format_result,
    _get_port,
    _ports,
    close,
    list_ports,
    open,
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
    return ser


def setup_function():
    _ports.clear()


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


def test_format_result_hex():
    result = _format_result(b"\x41\x42", "hex")
    assert result == {"length": 2, "data": "4142"}


def test_format_result_ascii():
    result = _format_result(b"AB", "ascii")
    assert result == {"length": 2, "data": "'AB'"}


def test_format_result_empty():
    result = _format_result(b"", "hex")
    assert result == {"length": 0, "data": ""}


# --- _get_port ---


def test_get_port_not_exists():
    assert _get_port("COM99") is None


def test_get_port_closed():
    mock = _make_mock_port(is_open=False)
    _ports["COM1"] = mock
    assert _get_port("COM1") is None
    assert "COM1" not in _ports


def test_get_port_open():
    mock = _make_mock_port(is_open=True)
    _ports["COM1"] = mock
    assert _get_port("COM1") is mock


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
    assert result[0]["status"] == "error"


# --- open ---


@patch("carrot_mcp_serial.server.serial.Serial")
def test_open_success(mock_serial_cls):
    mock_ser = _make_mock_port()
    mock_serial_cls.return_value = mock_ser

    result = open("COM3")
    assert result["status"] == "ok"
    assert result["port"] == "COM3"
    assert result["baudrate"] == 115200
    assert "COM3" in _ports


@patch("carrot_mcp_serial.server.serial.Serial")
def test_open_custom_params(mock_serial_cls):
    mock_ser = _make_mock_port()
    mock_serial_cls.return_value = mock_ser

    result = open("COM5", baudrate=9600, parity="E", stopbits=2)
    assert result["status"] == "ok"
    assert result["baudrate"] == 9600
    mock_serial_cls.assert_called_once_with(
        port="COM5", baudrate=9600, bytesize=8,
        parity="E", stopbits=2,
        timeout=1.0, write_timeout=1.0,
    )
    mock_ser.set_buffer_size.assert_called_once_with(rx_size=1048576, tx_size=1048576)


@patch("carrot_mcp_serial.server.serial.Serial")
def test_open_custom_buffer_size(mock_serial_cls):
    mock_ser = _make_mock_port()
    mock_serial_cls.return_value = mock_ser

    result = open("COM5", buffer_size=2097152)
    assert result["status"] == "ok"
    mock_ser.set_buffer_size.assert_called_once_with(rx_size=2097152, tx_size=2097152)


@patch("carrot_mcp_serial.server.serial.Serial")
def test_open_already_open(mock_serial_cls):
    mock_ser = _make_mock_port()
    _ports["COM3"] = mock_ser

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
    assert "COM99" not in _ports


# --- close ---


def test_close_success():
    mock_ser = _make_mock_port()
    _ports["COM3"] = mock_ser

    result = close("COM3")
    assert result["status"] == "ok"
    assert result["port"] == "COM3"
    assert "COM3" not in _ports
    mock_ser.close.assert_called_once()


def test_close_not_open():
    result = close("COM99")
    assert result["status"] == "error"
    assert "not open" in result["message"]


def test_close_exception_in_close():
    mock_ser = _make_mock_port()
    mock_ser.close.side_effect = Exception("close failed")
    _ports["COM3"] = mock_ser

    result = close("COM3")
    assert result["status"] == "ok"
    assert "COM3" not in _ports


# --- read ---


def test_read_success():
    mock_ser = _make_mock_port()
    mock_ser.read.return_value = b"\x48\x65\x6c\x6c\x6f"
    _ports["COM3"] = mock_ser

    result = read("COM3")
    assert result["status"] == "ok"
    assert result["data"] == "48656C6C6F"
    assert result["length"] == 5


def test_read_empty():
    mock_ser = _make_mock_port()
    mock_ser.read.return_value = b""
    _ports["COM3"] = mock_ser

    result = read("COM3")
    assert result["status"] == "ok"
    assert result["length"] == 0


def test_read_fmt_hex():
    mock_ser = _make_mock_port()
    mock_ser.read.return_value = b"\x01\x02"
    _ports["COM3"] = mock_ser

    result = read("COM3", fmt="hex")
    assert result["data"] == "0102"


def test_read_fmt_ascii():
    mock_ser = _make_mock_port()
    mock_ser.read.return_value = b"AB"
    _ports["COM3"] = mock_ser

    result = read("COM3", fmt="ascii")
    assert result["data"] == "'AB'"


def test_read_with_timeout_override():
    mock_ser = _make_mock_port()
    mock_ser.read.return_value = b"\x01"
    _ports["COM3"] = mock_ser

    result = read("COM3", timeout=2.0)
    assert result["status"] == "ok"
    assert mock_ser.timeout == 1.0


def test_read_not_open():
    result = read("COM99")
    assert result["status"] == "error"


def test_read_exception():
    mock_ser = _make_mock_port()
    mock_ser.read.side_effect = serial.SerialException("read failed")
    _ports["COM3"] = mock_ser

    result = read("COM3")
    assert result["status"] == "error"
    assert "COM3" not in _ports


# --- recv ---


def test_recv_success():
    mock_ser = _make_mock_port()
    mock_ser.in_waiting = 3
    mock_ser.read.return_value = b"\x01\x02\x03"
    _ports["COM3"] = mock_ser

    result = recv("COM3")
    assert result["status"] == "ok"
    assert result["data"] == "010203"
    assert result["length"] == 3
    mock_ser.read.assert_called_once_with(3)


def test_recv_empty_buffer():
    mock_ser = _make_mock_port()
    mock_ser.in_waiting = 0
    _ports["COM3"] = mock_ser

    result = recv("COM3")
    assert result["status"] == "ok"
    assert result["length"] == 0


def test_recv_with_size():
    mock_ser = _make_mock_port()
    mock_ser.read.return_value = b"\x01\x02"
    _ports["COM3"] = mock_ser

    result = recv("COM3", size=2)
    assert result["status"] == "ok"
    mock_ser.read.assert_called_once_with(2)


def test_recv_fmt_hex():
    mock_ser = _make_mock_port()
    mock_ser.in_waiting = 2
    mock_ser.read.return_value = b"\x41\x42"
    _ports["COM3"] = mock_ser

    result = recv("COM3", fmt="hex")
    assert result["data"] == "4142"


def test_recv_not_open():
    result = recv("COM99")
    assert result["status"] == "error"


def test_recv_exception():
    mock_ser = _make_mock_port()
    mock_ser.in_waiting = 1
    mock_ser.read.side_effect = serial.SerialException("recv failed")
    _ports["COM3"] = mock_ser

    result = recv("COM3")
    assert result["status"] == "error"
    assert "COM3" not in _ports


# --- write ---


def test_write_hex():
    mock_ser = _make_mock_port()
    mock_ser.write.return_value = 5
    _ports["COM3"] = mock_ser

    result = write("COM3", hex="48656C6C6F")
    assert result["status"] == "ok"
    assert result["bytes_written"] == 5
    mock_ser.write.assert_called_once_with(b"Hello")


def test_write_ascii():
    mock_ser = _make_mock_port()
    mock_ser.write.return_value = 5
    _ports["COM3"] = mock_ser

    result = write("COM3", ascii="Hello")
    assert result["status"] == "ok"
    assert result["bytes_written"] == 5
    mock_ser.write.assert_called_once_with(b"Hello")


def test_write_ascii_with_escape():
    mock_ser = _make_mock_port()
    mock_ser.write.return_value = 6
    _ports["COM3"] = mock_ser

    result = write("COM3", ascii="Hello\\n")
    assert result["status"] == "ok"
    mock_ser.write.assert_called_once_with(b"Hello\n")


def test_write_ascii_hex_escape():
    mock_ser = _make_mock_port()
    mock_ser.write.return_value = 1
    _ports["COM3"] = mock_ser

    result = write("COM3", ascii="\\x41")
    assert result["status"] == "ok"
    mock_ser.write.assert_called_once_with(b"A")


def test_write_both_params():
    mock_ser = _make_mock_port()
    _ports["COM3"] = mock_ser
    result = write("COM3", hex="41", ascii="A")
    assert result["status"] == "error"
    assert "only one" in result["message"]


def test_write_no_params():
    mock_ser = _make_mock_port()
    _ports["COM3"] = mock_ser
    result = write("COM3")
    assert result["status"] == "error"
    assert "Provide" in result["message"]


def test_write_invalid_hex():
    mock_ser = _make_mock_port()
    _ports["COM3"] = mock_ser
    result = write("COM3", hex="ZZZZ")
    assert result["status"] == "error"
    assert "Invalid hex" in result["message"]


def test_write_not_open():
    result = write("COM99", hex="41")
    assert result["status"] == "error"


def test_write_timeout():
    mock_ser = _make_mock_port()
    mock_ser.write.side_effect = serial.SerialTimeoutException("timeout")
    _ports["COM3"] = mock_ser

    result = write("COM3", hex="41")
    assert result["status"] == "error"
    assert "timed out" in result["message"]


def test_write_exception():
    mock_ser = _make_mock_port()
    mock_ser.write.side_effect = serial.SerialException("write failed")
    _ports["COM3"] = mock_ser

    result = write("COM3", hex="41")
    assert result["status"] == "error"
    assert "COM3" not in _ports


# --- script ---


def test_script_write_only():
    mock_ser = _make_mock_port()
    mock_ser.write.return_value = 2
    _ports["COM3"] = mock_ser

    steps = [{"op": "write", "data": "AA BB"}]
    result = script("COM3", steps)
    assert len(result) == 1
    assert result[0]["status"] == "ok"
    assert result[0]["bytes_written"] == 2
    mock_ser.write.assert_called_once_with(b"\xaa\xbb")


def test_script_wait():
    mock_ser = _make_mock_port()
    _ports["COM3"] = mock_ser

    steps = [{"op": "wait", "ms": 10}]
    result = script("COM3", steps)
    assert len(result) == 1
    assert result[0]["status"] == "ok"
    assert result[0]["ms"] == 10


def test_script_flush():
    mock_ser = _make_mock_port()
    _ports["COM3"] = mock_ser

    steps = [{"op": "flush"}]
    result = script("COM3", steps)
    assert len(result) == 1
    assert result[0]["status"] == "ok"
    mock_ser.reset_input_buffer.assert_called_once()
    mock_ser.reset_output_buffer.assert_called_once()


def test_script_read():
    mock_ser = _make_mock_port()
    mock_ser.read.return_value = b"\xAA\xBB"
    _ports["COM3"] = mock_ser

    steps = [{"op": "read", "size": 2, "timeout": 0.5}]
    result = script("COM3", steps)
    assert len(result) == 1
    assert result[0]["status"] == "ok"
    assert result[0]["data"] == "AABB"
    assert result[0]["length"] == 2


def test_script_read_with_match():
    mock_ser = _make_mock_port()
    mock_ser.read.return_value = b"\xAA\xBB"
    _ports["COM3"] = mock_ser

    steps = [{"op": "read", "size": 2, "timeout": 0.5, "expect": "AABB"}]
    result = script("COM3", steps)
    assert result[0]["matched"] is True


def test_script_read_no_match():
    mock_ser = _make_mock_port()
    mock_ser.read.return_value = b"\xAA\xBB"
    _ports["COM3"] = mock_ser

    steps = [{"op": "read", "size": 2, "timeout": 0.5, "expect": "CCDD"}]
    result = script("COM3", steps)
    assert result[0]["matched"] is False
    assert result[0]["expected"] == "CCDD"
    assert result[0]["status"] == "error"


def test_script_read_mismatch_stops():
    mock_ser = _make_mock_port()
    mock_ser.read.return_value = b"\xAA\xBB"
    _ports["COM3"] = mock_ser

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
    mock_ser = _make_mock_port()
    mock_ser.read.return_value = b"\xAA\xBB"
    mock_ser.write.return_value = 1
    _ports["COM3"] = mock_ser

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
    mock_ser = _make_mock_port()
    mock_ser.write.return_value = 1
    mock_ser.read.return_value = b"\xBB"
    _ports["COM3"] = mock_ser

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


def test_script_step_index():
    mock_ser = _make_mock_port()
    _ports["COM3"] = mock_ser

    steps = [{"op": "wait", "ms": 1}, {"op": "wait", "ms": 2}]
    result = script("COM3", steps)
    assert result[0]["step"] == 0
    assert result[1]["step"] == 1


def test_script_not_open():
    steps = [{"op": "wait", "ms": 1}]
    result = script("COM99", steps)
    assert result[0]["status"] == "error"
    assert "not open" in result[0]["message"]


def test_script_unknown_op():
    mock_ser = _make_mock_port()
    _ports["COM3"] = mock_ser

    steps = [{"op": "unknown"}]
    result = script("COM3", steps)
    assert result[0]["status"] == "error"
    assert "Unknown op" in result[0]["message"]


def test_script_exception_stops():
    mock_ser = _make_mock_port()
    mock_ser.write.side_effect = serial.SerialException("write failed")
    _ports["COM3"] = mock_ser

    steps = [
        {"op": "write", "data": "AA"},
        {"op": "wait", "ms": 10},
    ]
    result = script("COM3", steps)
    assert len(result) == 1
    assert result[0]["status"] == "error"
    assert "COM3" not in _ports


def test_script_ascii_fmt():
    mock_ser = _make_mock_port()
    mock_ser.write.return_value = 5
    _ports["COM3"] = mock_ser

    steps = [{"op": "write", "data": "Hello"}]
    result = script("COM3", steps, fmt="ascii")
    assert result[0]["status"] == "ok"
    mock_ser.write.assert_called_once_with(b"Hello")
