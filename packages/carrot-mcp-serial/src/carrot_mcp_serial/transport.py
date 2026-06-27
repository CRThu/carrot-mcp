"""Transport layer — raw I/O abstraction over serial hardware.

Transport is a pure FIFO interface: read, write, buffer status, close.
No wait/blocking semantics — that belongs to the Channel layer.
"""

from abc import ABC, abstractmethod

import serial


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

    def __init__(self, ser: serial.Serial):
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
