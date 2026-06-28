"""Tests for Transport layer."""

from unittest.mock import MagicMock, patch

from carrot_mcp_io.transport import SerialTransport, TcpTransport, UdpTransport


def _make_mock_ser(**kwargs):
    ser = MagicMock()
    ser.is_open = kwargs.get("is_open", True)
    ser.timeout = kwargs.get("timeout", 1.0)
    ser.in_waiting = kwargs.get("in_waiting", 0)
    return ser


# --- SerialTransport ---


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


# --- TcpTransport ---


def _make_mock_tcp_sock(**kwargs):
    sock = MagicMock()
    sock.fileno.return_value = kwargs.get("fileno", 3)
    sock.gettimeout.return_value = kwargs.get("timeout", 1.0)
    return sock


def test_tcp_is_open_true():
    sock = _make_mock_tcp_sock(fileno=3)
    t = TcpTransport(sock)
    assert t.is_open is True


def test_tcp_is_open_false():
    sock = _make_mock_tcp_sock()
    sock.fileno.side_effect = OSError("bad fd")
    t = TcpTransport(sock)
    assert t.is_open is False


def test_tcp_timeout_get():
    sock = _make_mock_tcp_sock(timeout=2.5)
    t = TcpTransport(sock)
    assert t.timeout == 2.5


def test_tcp_timeout_set():
    sock = _make_mock_tcp_sock()
    t = TcpTransport(sock)
    t.timeout = 0.5
    assert t.timeout == 0.5
    sock.settimeout.assert_called_with(0.5)


def test_tcp_in_waiting():
    sock = _make_mock_tcp_sock()
    sock.recv.side_effect = BlockingIOError
    t = TcpTransport(sock)
    assert t.in_waiting == 0


def test_tcp_in_waiting_with_data():
    sock = _make_mock_tcp_sock()
    call_count = 0

    def fake_recv(n):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return b"\x01\x02\x03"
        raise BlockingIOError

    sock.recv.side_effect = fake_recv
    t = TcpTransport(sock)
    assert t.in_waiting == 3


def test_tcp_read():
    sock = _make_mock_tcp_sock()
    sock.recv.side_effect = BlockingIOError
    t = TcpTransport(sock)
    t._rbuf.extend(b"\x01\x02\x03")
    data = t.read(2)
    assert data == b"\x01\x02"
    assert len(t._rbuf) == 1


def test_tcp_read_empty():
    sock = _make_mock_tcp_sock()
    sock.recv.side_effect = BlockingIOError
    t = TcpTransport(sock)
    data = t.read(10)
    assert data == b""


def test_tcp_write():
    sock = _make_mock_tcp_sock()
    t = TcpTransport(sock)
    n = t.write(b"Hello")
    assert n == 5
    sock.sendall.assert_called_once_with(b"Hello")


def test_tcp_reset_input_buffer():
    sock = _make_mock_tcp_sock()
    t = TcpTransport(sock)
    t._rbuf.extend(b"\x01\x02")
    t.reset_input_buffer()
    assert len(t._rbuf) == 0


def test_tcp_reset_output_buffer():
    sock = _make_mock_tcp_sock()
    t = TcpTransport(sock)
    t.reset_output_buffer()  # should not raise


def test_tcp_set_buffer_size():
    sock = _make_mock_tcp_sock()
    t = TcpTransport(sock)
    t.set_buffer_size(rx_size=2048, tx_size=4096)  # should not raise


def test_tcp_close():
    sock = _make_mock_tcp_sock()
    t = TcpTransport(sock)
    t.close()
    sock.close.assert_called_once()


def test_tcp_context_manager():
    sock = _make_mock_tcp_sock()
    t = TcpTransport(sock)
    with t:
        pass
    sock.close.assert_called_once()


# --- UdpTransport ---


def _make_mock_udp_sock(**kwargs):
    sock = MagicMock()
    sock.fileno.return_value = kwargs.get("fileno", 4)
    sock.gettimeout.return_value = kwargs.get("timeout", 1.0)
    return sock


def test_udp_is_open_true():
    sock = _make_mock_udp_sock(fileno=4)
    t = UdpTransport(sock, ("127.0.0.1", 5000))
    assert t.is_open is True


def test_udp_is_open_false():
    sock = _make_mock_udp_sock()
    sock.fileno.side_effect = OSError("bad fd")
    t = UdpTransport(sock, ("127.0.0.1", 5000))
    assert t.is_open is False


def test_udp_timeout_get():
    sock = _make_mock_udp_sock(timeout=2.5)
    t = UdpTransport(sock, ("127.0.0.1", 5000))
    assert t.timeout == 2.5


def test_udp_timeout_set():
    sock = _make_mock_udp_sock()
    t = UdpTransport(sock, ("127.0.0.1", 5000))
    t.timeout = 0.5
    assert t.timeout == 0.5
    sock.settimeout.assert_called_with(0.5)


def test_udp_in_waiting():
    sock = _make_mock_udp_sock()
    sock.recvfrom.side_effect = BlockingIOError
    t = UdpTransport(sock, ("127.0.0.1", 5000))
    assert t.in_waiting == 0


def test_udp_in_waiting_with_data():
    sock = _make_mock_udp_sock()
    call_count = 0

    def fake_recvfrom(n):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return (b"\x01\x02\x03", ("127.0.0.1", 5000))
        raise BlockingIOError

    sock.recvfrom.side_effect = fake_recvfrom
    t = UdpTransport(sock, ("127.0.0.1", 5000))
    assert t.in_waiting == 3


def test_udp_read():
    sock = _make_mock_udp_sock()
    sock.recvfrom.side_effect = BlockingIOError
    t = UdpTransport(sock, ("127.0.0.1", 5000))
    t._rbuf.extend(b"\x01\x02\x03")
    data = t.read(2)
    assert data == b"\x01\x02"
    assert len(t._rbuf) == 1


def test_udp_read_empty():
    sock = _make_mock_udp_sock()
    sock.recvfrom.side_effect = BlockingIOError
    t = UdpTransport(sock, ("127.0.0.1", 5000))
    data = t.read(10)
    assert data == b""


def test_udp_write():
    sock = _make_mock_udp_sock()
    t = UdpTransport(sock, ("127.0.0.1", 5000))
    n = t.write(b"Hello")
    assert n == 5
    sock.sendto.assert_called_once_with(b"Hello", ("127.0.0.1", 5000))


def test_udp_reset_input_buffer():
    sock = _make_mock_udp_sock()
    t = UdpTransport(sock, ("127.0.0.1", 5000))
    t._rbuf.extend(b"\x01\x02")
    t.reset_input_buffer()
    assert len(t._rbuf) == 0


def test_udp_close():
    sock = _make_mock_udp_sock()
    t = UdpTransport(sock, ("127.0.0.1", 5000))
    t.close()
    sock.close.assert_called_once()


def test_udp_context_manager():
    sock = _make_mock_udp_sock()
    t = UdpTransport(sock, ("127.0.0.1", 5000))
    with t:
        pass
    sock.close.assert_called_once()
