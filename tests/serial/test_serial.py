"""Tests for Carrot MCP Serial Server."""

from unittest.mock import MagicMock, patch

import serial

from carrot_mcp_serial.server import (
    _decode,
    _get_port,
    _ports,
    _to_ascii,
    _to_hex,
    close,
    list,
    open,
    read,
    recv,
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


# --- _to_hex / _to_ascii / _decode ---


def test_to_hex():
    assert _to_hex(b"\x48\x65\x6c\x6c\x6f") == "48656C6C6F"


def test_to_hex_empty():
    assert _to_hex(b"") == ""


def test_to_ascii_printable():
    assert _to_ascii(b"Hello") == "'Hello'"


def test_to_ascii_newline():
    assert _to_ascii(b"Hello\nWorld") == "'Hello\\nWorld'"


def test_to_ascii_null():
    assert _to_ascii(b"\x00") == "'\\x00'"


def test_to_ascii_mixed():
    assert _to_ascii(b"\x41\x00\x0a") == "'A\\x00\\n'"


def test_decode_hex():
    result = _decode(b"\x41\x42", "hex")
    assert result == {"length": 2, "data_hex": "4142"}


def test_decode_ascii():
    result = _decode(b"AB", "ascii")
    assert result == {"length": 2, "data_ascii": "'AB'"}


def test_decode_both():
    result = _decode(b"\x41\x00", "both")
    assert result == {"length": 2, "data_hex": "4100", "data_ascii": "'A\\x00'"}


def test_decode_empty():
    result = _decode(b"", "both")
    assert result == {"length": 0, "data_hex": "", "data_ascii": "''"}


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


# --- list ---


@patch("carrot_mcp_serial.server.serial.tools.list_ports.comports")
def test_list_ports(mock_comports):
    port1 = MagicMock()
    port1.device = "COM3"
    port1.description = "USB Serial"
    port1.hwid = "USB VID:PID=1234:5678"
    mock_comports.return_value = [port1]

    result = list()
    assert len(result) == 1
    assert result[0]["port"] == "COM3"
    assert result[0]["description"] == "USB Serial"


@patch("carrot_mcp_serial.server.serial.tools.list_ports.comports")
def test_list_ports_empty(mock_comports):
    mock_comports.return_value = []
    result = list()
    assert result == []


@patch("carrot_mcp_serial.server.serial.tools.list_ports.comports")
def test_list_ports_error(mock_comports):
    mock_comports.side_effect = Exception("access denied")
    result = list()
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
    assert result["data_hex"] == "48656C6C6F"
    assert result["data_ascii"] == "'Hello'"
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
    assert "data_hex" in result
    assert "data_ascii" not in result


def test_read_fmt_ascii():
    mock_ser = _make_mock_port()
    mock_ser.read.return_value = b"AB"
    _ports["COM3"] = mock_ser

    result = read("COM3", fmt="ascii")
    assert "data_ascii" in result
    assert "data_hex" not in result


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
    assert result["data_hex"] == "010203"
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
    assert "data_hex" in result
    assert "data_ascii" not in result


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
