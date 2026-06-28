"""Transport layer — raw I/O abstraction over hardware and network.

Transport is a pure FIFO interface: read, write, buffer status, close.
No wait/blocking semantics — that belongs to the Channel layer.
"""

from abc import ABC, abstractmethod
import socket


class Transport(ABC):
    """Abstract FIFO transport for reading/writing raw bytes."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @abstractmethod
    def read(self, size: int) -> bytes:
        """Read up to size bytes from hardware (blocking up to timeout)."""

    @abstractmethod
    def write(self, data: bytes) -> int:
        """Write data to hardware. Returns bytes written."""

    @abstractmethod
    def reset_input_buffer(self) -> None:
        """Discard all data in the input buffer."""

    @abstractmethod
    def reset_output_buffer(self) -> None:
        """Discard all data in the output buffer."""

    @abstractmethod
    def set_buffer_size(self, rx_size: int, tx_size: int) -> None:
        """Set hardware buffer sizes."""

    @property
    @abstractmethod
    def is_open(self) -> bool:
        """Whether the transport is open."""

    @property
    @abstractmethod
    def timeout(self) -> float | None:
        """Read timeout in seconds."""

    @timeout.setter
    @abstractmethod
    def timeout(self, value: float | None) -> None:
        """Set read timeout in seconds."""

    @property
    @abstractmethod
    def in_waiting(self) -> int:
        """Number of bytes waiting in hardware input buffer."""

    @property
    @abstractmethod
    def out_waiting(self) -> int:
        """Number of bytes waiting in hardware output buffer."""

    @abstractmethod
    def close(self) -> None:
        """Close the transport."""


class SerialTransport(Transport):
    """pyserial-backed transport."""

    def __init__(self, ser):
        self._ser = ser

    @property
    def is_open(self) -> bool:
        return self._ser.is_open

    @property
    def timeout(self) -> float | None:
        return self._ser.timeout

    @timeout.setter
    def timeout(self, value: float | None) -> None:
        self._ser.timeout = value

    @property
    def in_waiting(self) -> int:
        return self._ser.in_waiting

    @property
    def out_waiting(self) -> int:
        return self._ser.out_waiting

    def read(self, size: int) -> bytes:
        return self._ser.read(size)

    def write(self, data: bytes) -> int:
        return self._ser.write(data)

    def reset_input_buffer(self) -> None:
        self._ser.reset_input_buffer()

    def reset_output_buffer(self) -> None:
        self._ser.reset_output_buffer()

    def set_buffer_size(self, rx_size: int, tx_size: int) -> None:
        self._ser.set_buffer_size(rx_size=rx_size, tx_size=tx_size)

    def close(self) -> None:
        self._ser.close()


class TcpTransport(Transport):
    """TCP socket transport."""

    def __init__(self, sock: socket.socket):
        self._sock = sock
        self._rbuf = bytearray()
        self._timeout: float | None = sock.gettimeout()

    @property
    def is_open(self) -> bool:
        try:
            self._sock.fileno()
            return True
        except OSError:
            return False

    @property
    def timeout(self) -> float | None:
        return self._timeout

    @timeout.setter
    def timeout(self, value: float | None) -> None:
        self._timeout = value
        self._sock.settimeout(value)

    def _fill_rbuf(self) -> None:
        """Non-blocking recv to fill read buffer."""
        self._sock.setblocking(False)
        try:
            while True:
                chunk = self._sock.recv(65536)
                if not chunk:
                    break
                self._rbuf.extend(chunk)
        except (BlockingIOError, OSError):
            pass
        finally:
            self._sock.settimeout(self._timeout)

    @property
    def in_waiting(self) -> int:
        self._fill_rbuf()
        return len(self._rbuf)

    @property
    def out_waiting(self) -> int:
        return 0

    def read(self, size: int) -> bytes:
        self._fill_rbuf()
        if not self._rbuf:
            return b""
        n = min(size, len(self._rbuf))
        data = bytes(self._rbuf[:n])
        del self._rbuf[:n]
        return data

    def write(self, data: bytes) -> int:
        self._sock.sendall(data)
        return len(data)

    def reset_input_buffer(self) -> None:
        self._rbuf.clear()

    def reset_output_buffer(self) -> None:
        pass

    def set_buffer_size(self, rx_size: int, tx_size: int) -> None:
        pass

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass


class UdpTransport(Transport):
    """UDP socket transport."""

    def __init__(self, sock: socket.socket, remote_addr: tuple[str, int]):
        self._sock = sock
        self._remote_addr = remote_addr
        self._rbuf = bytearray()
        self._timeout: float | None = sock.gettimeout()

    @property
    def is_open(self) -> bool:
        try:
            self._sock.fileno()
            return True
        except OSError:
            return False

    @property
    def timeout(self) -> float | None:
        return self._timeout

    @timeout.setter
    def timeout(self, value: float | None) -> None:
        self._timeout = value
        self._sock.settimeout(value)

    def _fill_rbuf(self) -> None:
        """Non-blocking recvfrom to fill read buffer."""
        self._sock.setblocking(False)
        try:
            while True:
                data, _ = self._sock.recvfrom(65536)
                if not data:
                    break
                self._rbuf.extend(data)
        except (BlockingIOError, OSError):
            pass
        finally:
            self._sock.settimeout(self._timeout)

    @property
    def in_waiting(self) -> int:
        self._fill_rbuf()
        return len(self._rbuf)

    @property
    def out_waiting(self) -> int:
        return 0

    def read(self, size: int) -> bytes:
        self._fill_rbuf()
        if not self._rbuf:
            return b""
        n = min(size, len(self._rbuf))
        data = bytes(self._rbuf[:n])
        del self._rbuf[:n]
        return data

    def write(self, data: bytes) -> int:
        self._sock.sendto(data, self._remote_addr)
        return len(data)

    def reset_input_buffer(self) -> None:
        self._rbuf.clear()

    def reset_output_buffer(self) -> None:
        pass

    def set_buffer_size(self, rx_size: int, tx_size: int) -> None:
        pass

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass
