"""Channel layer — buffered I/O with observer support.

Channel wraps a Transport and provides:
- RX/TX application-level buffers (deque-based, backpressure-enabled)
- Background polling via daemon thread
- Observer pattern for event notifications (decoupled logging)
- Event-driven wait for read/write completion (no busy-wait)

Backpressure model:
- RX: when buffer is full, poll thread stops reading from hardware.
  Data stays in OS/hardware buffer until consumer frees space.
- TX: when buffer is full, write() blocks until drain creates space.

RX and TX use independent locks so read/write paths never contend.
"""

from collections import deque
import threading
import time
from typing import Callable

from .transport import Transport


class ChannelEvent:
    """Event emitted by Channel for observer consumption."""

    __slots__ = ("ts", "op", "data", "length", "pending")

    def __init__(self, op: str, data: bytes, pending: int):
        self.ts = time.time()
        self.op = op
        self.data = data
        self.length = len(data)
        self.pending = pending

    def to_dict(self) -> dict:
        return {
            "ts": self.ts,
            "op": self.op,
            "data": self.data.hex().upper(),
            "length": self.length,
            "pending": self.pending,
        }


Observer = Callable[[ChannelEvent], None]


class Channel:
    """Buffered channel over a Transport with backpressure and observer support.

    The outside world reads/writes through this channel.
    Background polling fills the RX buffer from hardware and drains TX buffer to hardware.
    All hardware I/O is performed by the poll thread — callers only touch buffers.

    Backpressure:
    - RX buffer full → poll thread stops reading (data stays in OS serial buffer)
    - TX buffer full → tx_enqueue() blocks until drain creates space
    """

    def __init__(
        self,
        transport: Transport,
        rx_maxlen: int = 1024 * 1024,
        tx_maxlen: int = 1024 * 1024,
        poll_interval: float = 0.005,
        read_timeout: float | None = None,
        write_timeout: float | None = None,
    ):
        self._transport = transport
        self._rx_maxlen = rx_maxlen
        self._tx_maxlen = tx_maxlen
        self._rx: deque[bytes] = deque()
        self._tx: deque[bytes] = deque()
        self._poll_interval = poll_interval
        self._read_timeout = read_timeout
        self._write_timeout = write_timeout
        self._rx_lock = threading.Lock()
        self._tx_lock = threading.Lock()
        self._tx_cond = threading.Condition(self._tx_lock)
        self._observers: list[Observer] = []

        self._shutdown = threading.Event()
        self._data_ready = threading.Event()
        self._drain_done = threading.Event()
        self._total_tx: int = 0
        self._total_rx: int = 0
        self._write_error: Exception | None = None
        self._thread: threading.Thread | None = None
        self._write_lock = threading.Lock()

    @property
    def is_open(self) -> bool:
        return self._transport.is_open

    @property
    def read_timeout(self) -> float | None:
        return self._read_timeout

    @property
    def write_timeout(self) -> float | None:
        return self._write_timeout

    # --- Observer management ---

    def attach(self, observer: Observer) -> None:
        """Register an event observer."""
        self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        """Unregister an event observer."""
        self._observers.remove(observer)

    def _emit(self, event: ChannelEvent) -> None:
        """Notify all observers of an event."""
        for observer in self._observers:
            try:
                observer(event)
            except Exception:
                pass

    # --- Polling ---

    def start(self) -> None:
        """Start background polling daemon thread."""
        if self._thread is not None:
            return
        self._shutdown.clear()
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="channel-poll",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop background polling."""
        if self._thread is None:
            return
        self._shutdown.set()
        self._thread.join(timeout=2.0)
        self._thread = None

    def _poll_loop(self) -> None:
        """Poll hardware: drain TX buffer to hardware, fill RX buffer from hardware."""
        while not self._shutdown.is_set():
            try:
                self._drain_tx()
            except Exception:
                pass
            try:
                self._fill_rx()
            except Exception:
                pass
            self._shutdown.wait(self._poll_interval)

    # --- TX drain (poll thread only) ---

    def _drain_tx(self) -> None:
        """Drain one chunk from TX buffer to hardware."""
        with self._tx_lock:
            if not self._tx:
                return
            if self._transport.out_waiting > 0:
                return
            data = self._tx.popleft()
        try:
            self._transport.write(data)
            with self._tx_lock:
                self._total_tx += len(data)
                self._write_error = None
                pending = sum(len(c) for c in self._tx)
            self._emit(ChannelEvent("tx_drain", data, pending))
        except Exception as e:
            with self._tx_lock:
                self._tx.appendleft(data)
                self._write_error = e
        finally:
            with self._tx_lock:
                self._tx_cond.notify_all()
            self._drain_done.set()

    # --- RX fill (poll thread only) ---

    def _fill_rx(self) -> None:
        """Read from hardware into RX buffer. Skips when buffer is full (backpressure)."""
        with self._rx_lock:
            if sum(len(c) for c in self._rx) >= self._rx_maxlen:
                return
        n = self._transport.in_waiting
        if n > 0:
            data = self._transport.read(n)
            if data:
                with self._rx_lock:
                    self._rx.append(data)
                    self._total_rx += len(data)
                    pending = sum(len(c) for c in self._rx)
                self._emit(ChannelEvent("recv", data, pending))
                self._data_ready.set()

    # --- RX buffer operations ---

    def read(self, size: int) -> bytes:
        """Read up to size bytes from RX buffer (non-blocking)."""
        with self._rx_lock:
            chunks = []
            remaining = size
            while self._rx and remaining > 0:
                chunk = self._rx.popleft()
                if len(chunk) <= remaining:
                    chunks.append(chunk)
                    remaining -= len(chunk)
                else:
                    chunks.append(chunk[:remaining])
                    self._rx.appendleft(chunk[remaining:])
                    remaining = 0
            data = b"".join(chunks)
            pending = sum(len(c) for c in self._rx)
        if data:
            self._emit(ChannelEvent("read", data, pending))
        return data

    def wait_read(self, size: int, timeout: float) -> bytes:
        """Wait for data to arrive, then read. Event-driven, no busy-wait."""
        deadline = time.monotonic() + timeout
        while True:
            with self._rx_lock:
                self._data_ready.clear()
            data = self.read(size)
            if data:
                return data
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return b""
            self._data_ready.wait(timeout=min(remaining, 0.1))

    def read_all(self) -> bytes:
        """Read all available data from RX buffer."""
        with self._rx_lock:
            chunks = list(self._rx)
            self._rx.clear()
            data = b"".join(chunks)
        if data:
            self._emit(ChannelEvent("read", data, 0))
        return data

    def peek(self, size: int | None = None) -> bytes:
        """Peek at RX buffer data without consuming."""
        with self._rx_lock:
            if size is None:
                return b"".join(self._rx)
            chunks = []
            remaining = size
            for chunk in self._rx:
                if remaining <= 0:
                    break
                chunks.append(chunk[:remaining])
                remaining -= len(chunk)
            return b"".join(chunks)

    @property
    def rx_pending(self) -> int:
        """Number of bytes waiting in RX buffer."""
        with self._rx_lock:
            return sum(len(c) for c in self._rx)

    @property
    def pending(self) -> int:
        """Alias for rx_pending."""
        return self.rx_pending

    # --- TX buffer operations ---

    def tx_enqueue(self, data: bytes) -> int:
        """Enqueue data into TX buffer. Blocks if buffer is full (backpressure)."""
        with self._tx_cond:
            while sum(len(c) for c in self._tx) + len(data) > self._tx_maxlen:
                if not self._tx_cond.wait(timeout=self._write_timeout):
                    raise TimeoutError("TX buffer full, write timed out")
            self._tx.append(data)
            self._tx_cond.notify_all()
        self._emit(ChannelEvent("tx_queue", data, sum(len(c) for c in self._tx)))
        return len(data)

    def tx_dequeue(self, size: int) -> bytes:
        """Dequeue up to size bytes from TX buffer."""
        with self._tx_lock:
            chunks = []
            remaining = size
            while self._tx and remaining > 0:
                chunk = self._tx.popleft()
                if len(chunk) <= remaining:
                    chunks.append(chunk)
                    remaining -= len(chunk)
                else:
                    chunks.append(chunk[:remaining])
                    self._tx.appendleft(chunk[remaining:])
                    remaining = 0
            return b"".join(chunks)

    @property
    def tx_pending(self) -> int:
        """Number of bytes waiting in TX buffer."""
        with self._tx_lock:
            return sum(len(c) for c in self._tx)

    # --- Hardware passthrough ---

    def write(self, data: bytes) -> int:
        """Enqueue data into TX buffer, wait for drain, return bytes written."""
        with self._write_lock:
            n = self.tx_enqueue(data)
            self._drain_done.clear()
            self._drain_done.wait(timeout=self._write_timeout)
            with self._tx_lock:
                if self._write_error is not None:
                    err = self._write_error
                    self._write_error = None
                    raise err
            return n

    def flush(self) -> None:
        """Wait until TX buffer is fully drained. Event-driven, no busy-wait."""
        with self._write_lock:
            while True:
                self._drain_done.clear()
                with self._tx_lock:
                    if not self._tx:
                        return
                self._drain_done.wait(timeout=0.1)

    def reset_input_buffer(self) -> None:
        """Reset hardware input buffer."""
        self._transport.reset_input_buffer()

    def reset_output_buffer(self) -> None:
        """Reset hardware output buffer."""
        self._transport.reset_output_buffer()

    def set_buffer_size(self, rx_size: int, tx_size: int) -> None:
        """Set hardware buffer sizes."""
        self._transport.set_buffer_size(rx_size=rx_size, tx_size=tx_size)

    @property
    def total_tx(self) -> int:
        """Total bytes sent to hardware."""
        with self._tx_lock:
            return self._total_tx

    @property
    def total_rx(self) -> int:
        """Total bytes received from hardware."""
        with self._rx_lock:
            return self._total_rx

    def close(self) -> None:
        """Stop polling and close transport."""
        self.stop()
        self._transport.close()
