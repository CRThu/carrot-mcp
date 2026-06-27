"""Tests for Transport layer."""

from unittest.mock import MagicMock

from carrot_mcp_serial.transport import SerialTransport


def _make_mock_ser(**kwargs):
    ser = MagicMock()
    ser.is_open = kwargs.get("is_open", True)
    ser.timeout = kwargs.get("timeout", 1.0)
    ser.in_waiting = kwargs.get("in_waiting", 0)
    return ser


def test_is_open_true():
    ser = _make_mock_ser(is_open=True)
    t = SerialTransport(ser)
    assert t.is_open is True


def test_is_open_false():
    ser = _make_mock_ser(is_open=False)
    t = SerialTransport(ser)
    assert t.is_open is False


def test_timeout_get():
    ser = _make_mock_ser(timeout=2.5)
    t = SerialTransport(ser)
    assert t.timeout == 2.5


def test_timeout_set():
    ser = _make_mock_ser()
    t = SerialTransport(ser)
    t.timeout = 0.5
    assert ser.timeout == 0.5


def test_timeout_set_none():
    ser = _make_mock_ser()
    t = SerialTransport(ser)
    t.timeout = None
    assert ser.timeout is None


def test_in_waiting():
    ser = _make_mock_ser(in_waiting=42)
    t = SerialTransport(ser)
    assert t.in_waiting == 42


def test_out_waiting():
    ser = _make_mock_ser()
    ser.out_waiting = 17
    t = SerialTransport(ser)
    assert t.out_waiting == 17


def test_read():
    ser = _make_mock_ser()
    ser.read.return_value = b"\x01\x02\x03"
    t = SerialTransport(ser)
    data = t.read(10)
    assert data == b"\x01\x02\x03"
    ser.read.assert_called_once_with(10)


def test_write():
    ser = _make_mock_ser()
    ser.write.return_value = 5
    t = SerialTransport(ser)
    n = t.write(b"Hello")
    assert n == 5
    ser.write.assert_called_once_with(b"Hello")


def test_reset_input_buffer():
    ser = _make_mock_ser()
    t = SerialTransport(ser)
    t.reset_input_buffer()
    ser.reset_input_buffer.assert_called_once()


def test_reset_output_buffer():
    ser = _make_mock_ser()
    t = SerialTransport(ser)
    t.reset_output_buffer()
    ser.reset_output_buffer.assert_called_once()


def test_set_buffer_size():
    ser = _make_mock_ser()
    t = SerialTransport(ser)
    t.set_buffer_size(rx_size=2048, tx_size=4096)
    ser.set_buffer_size.assert_called_once_with(rx_size=2048, tx_size=4096)


def test_close():
    ser = _make_mock_ser()
    t = SerialTransport(ser)
    t.close()
    ser.close.assert_called_once()


def test_context_manager():
    ser = _make_mock_ser()
    t = SerialTransport(ser)
    with t:
        pass
    ser.close.assert_called_once()
