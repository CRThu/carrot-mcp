"""Tests for Channel layer."""

import threading
import time
from unittest.mock import MagicMock

from carrot_mcp_serial.channel import Channel, ChannelEvent
from carrot_mcp_serial.transport import SerialTransport


def _make_mock_ser(**kwargs):
    ser = MagicMock()
    ser.is_open = kwargs.get("is_open", True)
    ser.timeout = kwargs.get("timeout", 1.0)
    ser.in_waiting = kwargs.get("in_waiting", 0)
    ser.out_waiting = kwargs.get("out_waiting", 0)
    return ser


def _make_channel(**kwargs):
    ser = _make_mock_ser(**kwargs)
    transport = SerialTransport(ser)
    ch = Channel(
        transport,
        rx_maxlen=kwargs.get("rx_maxlen", 1024),
        tx_maxlen=kwargs.get("tx_maxlen", 1024),
        poll_interval=kwargs.get("poll_interval", 0.005),
        read_timeout=kwargs.get("read_timeout", 1.0),
        write_timeout=kwargs.get("write_timeout", 1.0),
    )
    return ch, ser


# --- ChannelEvent ---


def test_channel_event_fields():
    e = ChannelEvent("recv", b"\x01\x02", pending=10)
    assert e.op == "recv"
    assert e.data == b"\x01\x02"
    assert e.length == 2
    assert e.pending == 10
    assert isinstance(e.ts, float)


def test_channel_event_to_dict():
    e = ChannelEvent("write", b"\xAB\xCD", pending=5)
    d = e.to_dict()
    assert d["op"] == "write"
    assert d["data"] == "ABCD"
    assert d["length"] == 2
    assert d["pending"] == 5
    assert "ts" in d


def test_channel_event_empty_data():
    e = ChannelEvent("read", b"", pending=0)
    assert e.length == 0
    assert e.to_dict()["data"] == ""


# --- Properties ---


def test_is_open():
    ch, _ = _make_channel(is_open=True)
    assert ch.is_open is True


def test_is_open_false():
    ch, _ = _make_channel(is_open=False)
    assert ch.is_open is False


def test_read_timeout():
    ch, _ = _make_channel(read_timeout=2.5)
    assert ch.read_timeout == 2.5


def test_write_timeout():
    ch, _ = _make_channel(write_timeout=0.5)
    assert ch.write_timeout == 0.5


def test_read_timeout_default():
    ch, _ = _make_channel()
    assert ch.read_timeout == 1.0


def test_write_timeout_default():
    ch, _ = _make_channel()
    assert ch.write_timeout == 1.0


# --- RX buffer ---


def test_rx_pending():
    ch, _ = _make_channel()
    ch._rx.append(b"\x01\x02\x03")
    assert ch.rx_pending == 3


def test_rx_pending_empty():
    ch, _ = _make_channel()
    assert ch.rx_pending == 0


def test_pending_alias():
    ch, _ = _make_channel()
    ch._rx.append(b"\x01\x02")
    assert ch.pending == ch.rx_pending


def test_read_exact():
    ch, _ = _make_channel()
    ch._rx.append(b"\x01\x02\x03")
    data = ch.read(3)
    assert data == b"\x01\x02\x03"
    assert ch.rx_pending == 0


def test_read_partial():
    ch, _ = _make_channel()
    ch._rx.append(b"\x01\x02\x03")
    data = ch.read(2)
    assert data == b"\x01\x02"
    assert ch.rx_pending == 1


def test_read_more_than_available():
    ch, _ = _make_channel()
    ch._rx.append(b"\x01\x02")
    data = ch.read(100)
    assert data == b"\x01\x02"
    assert ch.rx_pending == 0


def test_read_empty():
    ch, _ = _make_channel()
    data = ch.read(10)
    assert data == b""


def test_read_multiple_chunks():
    ch, _ = _make_channel()
    ch._rx.append(b"\x01\x02")
    ch._rx.append(b"\x03\x04")
    ch._rx.append(b"\x05")
    data = ch.read(4)
    assert data == b"\x01\x02\x03\x04"
    assert ch.rx_pending == 1


def test_read_chunk_boundary():
    ch, _ = _make_channel()
    ch._rx.append(b"\x01\x02\x03")
    data = ch.read(2)
    assert data == b"\x01\x02"
    data = ch.read(2)
    assert data == b"\x03"


def test_read_all():
    ch, _ = _make_channel()
    ch._rx.append(b"\x01\x02")
    ch._rx.append(b"\x03")
    data = ch.read_all()
    assert data == b"\x01\x02\x03"
    assert ch.rx_pending == 0


def test_read_all_empty():
    ch, _ = _make_channel()
    data = ch.read_all()
    assert data == b""


def test_peek():
    ch, _ = _make_channel()
    ch._rx.append(b"\x01\x02\x03")
    data = ch.peek(2)
    assert data == b"\x01\x02"
    assert ch.rx_pending == 3  # peek doesn't consume


def test_peek_all():
    ch, _ = _make_channel()
    ch._rx.append(b"\x01\x02")
    data = ch.peek()
    assert data == b"\x01\x02"


def test_peek_empty():
    ch, _ = _make_channel()
    data = ch.peek()
    assert data == b""


def test_peek_more_than_available():
    ch, _ = _make_channel()
    ch._rx.append(b"\x01")
    data = ch.peek(100)
    assert data == b"\x01"


# --- TX buffer ---


def test_tx_enqueue():
    ch, _ = _make_channel()
    n = ch.tx_enqueue(b"\x01\x02")
    assert n == 2
    assert ch.tx_pending == 2


def test_tx_dequeue():
    ch, _ = _make_channel()
    ch.tx_enqueue(b"\x01\x02\x03")
    data = ch.tx_dequeue(2)
    assert data == b"\x01\x02"
    assert ch.tx_pending == 1


def test_tx_dequeue_all():
    ch, _ = _make_channel()
    ch.tx_enqueue(b"\x01\x02")
    data = ch.tx_dequeue(100)
    assert data == b"\x01\x02"
    assert ch.tx_pending == 0


def test_tx_dequeue_empty():
    ch, _ = _make_channel()
    data = ch.tx_dequeue(10)
    assert data == b""


def test_tx_pending():
    ch, _ = _make_channel()
    assert ch.tx_pending == 0
    ch.tx_enqueue(b"\x01\x02\x03")
    assert ch.tx_pending == 3


# --- Hardware passthrough ---


def test_write():
    ch, ser = _make_channel()
    ser.write.return_value = 5
    ch.start()
    n = ch.write(b"Hello")
    ch.stop()
    assert n == 5
    ser.write.assert_called_once_with(b"Hello")


def test_reset_input_buffer():
    ch, ser = _make_channel()
    ch.reset_input_buffer()
    ser.reset_input_buffer.assert_called_once()


def test_reset_output_buffer():
    ch, ser = _make_channel()
    ch.reset_output_buffer()
    ser.reset_output_buffer.assert_called_once()


def test_set_buffer_size():
    ch, ser = _make_channel()
    ch.set_buffer_size(2048, 4096)
    ser.set_buffer_size.assert_called_once_with(rx_size=2048, tx_size=4096)


# --- Observer ---


def test_observer_receives_events():
    ch, _ = _make_channel()
    events = []
    ch.attach(lambda e: events.append(e))

    ch._rx.append(b"\x01")
    ch.read(1)

    assert len(events) == 1
    assert events[0].op == "read"
    assert events[0].data == b"\x01"


def test_observer_multiple():
    ch, _ = _make_channel()
    events_a = []
    events_b = []
    ch.attach(lambda e: events_a.append(e))
    ch.attach(lambda e: events_b.append(e))

    ch._rx.append(b"\x01")
    ch.read(1)

    assert len(events_a) == 1
    assert len(events_b) == 1


def test_detach_observer():
    ch, _ = _make_channel()
    events = []
    observer = lambda e: events.append(e)
    ch.attach(observer)
    ch.detach(observer)

    ch._rx.append(b"\x01")
    ch.read(1)

    assert len(events) == 0


def test_detach_nonexistent_observer():
    ch, _ = _make_channel()
    observer = lambda e: None
    ch.detach(observer)  # should not raise


def test_detach_twice():
    ch, _ = _make_channel()
    events = []
    observer = lambda e: events.append(e)
    ch.attach(observer)
    ch.detach(observer)
    ch.detach(observer)  # second detach should not raise

    ch._rx.append(b"\x01")
    ch.read(1)
    assert len(events) == 0


def test_observer_exception_doesnt_crash():
    ch, _ = _make_channel()
    good_events = []

    def bad_observer(e):
        raise RuntimeError("boom")

    ch.attach(bad_observer)
    ch.attach(lambda e: good_events.append(e))

    ch._rx.append(b"\x01")
    ch.read(1)

    assert len(good_events) == 1


def test_observer_on_write():
    ch, ser = _make_channel()
    ser.write.return_value = 5
    events = []
    ch.attach(lambda e: events.append(e))

    ch.start()
    ch.write(b"Hello")
    ch.stop()

    assert any(e.op == "tx_queue" for e in events)


# --- Polling lifecycle ---


def test_start_stop():
    ch, _ = _make_channel()
    ch.start()
    assert ch._thread is not None
    ch.stop()
    assert ch._thread is None


def test_start_idempotent():
    ch, _ = _make_channel()
    ch.start()
    thread1 = ch._thread
    ch.start()
    assert ch._thread is thread1
    ch.stop()


def test_stop_when_not_started():
    ch, _ = _make_channel()
    ch.stop()  # should not raise


def test_close():
    ch, ser = _make_channel()
    ch.start()
    ch.close()
    ser.close.assert_called_once()
    assert ch._thread is None


def test_poll_fills_rx():
    ch, ser = _make_channel(poll_interval=0.001)
    ser.in_waiting = 3
    ser.read.return_value = b"\x01\x02\x03"
    ch.start()
    time.sleep(0.02)
    ch.stop()
    assert ch.rx_pending >= 3


def test_poll_drains_tx():
    ch, ser = _make_channel(poll_interval=0.001)
    ser.write.return_value = 2
    ch.tx_enqueue(b"\xAA\xBB")
    ch.start()
    time.sleep(0.05)
    ch.stop()
    assert ch.tx_pending == 0
    ser.write.assert_called_with(b"\xAA\xBB")


def test_poll_tx_write_failure_keeps_data():
    ch, ser = _make_channel(poll_interval=0.001)
    ser.write.side_effect = Exception("write failed")
    ch.tx_enqueue(b"\xAA")
    ch.start()
    time.sleep(0.05)
    ch.stop()
    assert ch.tx_pending == 1  # data put back


def test_observer_on_poll_recv():
    ch, ser = _make_channel(poll_interval=0.001)
    ser.in_waiting = 2
    ser.read.return_value = b"\x01\x02"
    events = []
    ch.attach(lambda e: events.append(e))
    ch.start()
    time.sleep(0.05)
    ch.stop()
    assert any(e.op == "recv" for e in events)


# --- Backpressure ---


def test_rx_backpressure_skips_read_when_full():
    ch, ser = _make_channel(rx_maxlen=6, poll_interval=0.001)
    ser.in_waiting = 10
    ser.read.return_value = b"\x01\x02\x03\x04\x05\x06"
    ch.start()
    time.sleep(0.05)
    ch.stop()
    assert ch.rx_pending == 6
    ser.read.assert_called_once_with(10)


def test_rx_backpressure_resumes_after_read():
    ch, ser = _make_channel(rx_maxlen=6, poll_interval=0.001)
    read_count = 0

    def fake_in_waiting():
        pending = sum(len(c) for c in ch._rx)
        if pending >= 6:
            return 0
        return 3

    def fake_read(n):
        nonlocal read_count
        read_count += 1
        return b"\x01\x02\x03"

    type(ser).in_waiting = property(lambda self: fake_in_waiting())
    ser.read.side_effect = fake_read
    ch.start()
    time.sleep(0.05)
    assert ch.rx_pending == 6

    ch.read(3)
    time.sleep(0.05)
    ch.stop()
    assert ch.rx_pending == 6


def test_tx_backpressure_blocks_when_full():
    ch, ser = _make_channel(tx_maxlen=4, poll_interval=0.001, write_timeout=2.0)
    ser.write.return_value = 2
    ch.tx_enqueue(b"\x01\x02\x03\x04")
    assert ch.tx_pending == 4

    blocked = threading.Event()
    unblocked = threading.Event()

    def enqueue_blocking():
        blocked.set()
        ch.tx_enqueue(b"\x05\x06")
        unblocked.set()

    t = threading.Thread(target=enqueue_blocking)
    t.start()
    blocked.wait(timeout=1.0)
    time.sleep(0.05)
    assert not unblocked.is_set()

    ch.start()
    time.sleep(0.2)
    assert unblocked.is_set()
    t.join(timeout=2.0)
    ch.stop()


def test_tx_enqueue_timeout_when_full():
    ch, ser = _make_channel(tx_maxlen=4, write_timeout=0.05)
    ch.tx_enqueue(b"\x01\x02\x03\x04")
    assert ch.tx_pending == 4
    try:
        ch.tx_enqueue(b"\x05\x06")
        assert False, "Should have raised TimeoutError"
    except TimeoutError:
        pass


# --- wait_read ---


def test_wait_read_immediate():
    ch, _ = _make_channel()
    ch._rx.append(b"\x01\x02")
    data = ch.wait_read(2, timeout=1.0)
    assert data == b"\x01\x02"


def test_wait_read_timeout():
    ch, _ = _make_channel()
    data = ch.wait_read(1, timeout=0.01)
    assert data == b""


def test_wait_read_arrives_later():
    ch, _ = _make_channel(poll_interval=0.001)
    ser = ch._transport._ser
    ser.in_waiting = 2
    ser.read.return_value = b"\xAA\xBB"
    ch.start()
    data = ch.wait_read(2, timeout=0.5)
    ch.stop()
    assert data == b"\xAA\xBB"


# --- flush ---


def test_flush_empty():
    ch, _ = _make_channel()
    ch.flush()  # should return immediately


def test_flush_waits_for_drain():
    ch, ser = _make_channel(poll_interval=0.001)
    ser.write.return_value = 2
    ch.tx_enqueue(b"\xAA\xBB")
    ch.start()
    ch.flush()
    ch.stop()
    assert ch.tx_pending == 0


# --- total_tx / total_rx ---


def test_total_tx():
    ch, ser = _make_channel(poll_interval=0.001)
    ser.write.return_value = 3
    ch.tx_enqueue(b"\x01\x02\x03")
    ch.start()
    time.sleep(0.05)
    ch.stop()
    assert ch.total_tx == 3


def test_total_rx():
    ch, ser = _make_channel(poll_interval=0.001)
    call_count = 0

    def fake_in_waiting():
        nonlocal call_count
        if call_count == 0:
            return 2
        return 0

    def fake_read(n):
        nonlocal call_count
        call_count += 1
        return b"\x01\x02"

    type(ser).in_waiting = property(lambda self: fake_in_waiting())
    ser.read.side_effect = fake_read
    ch.start()
    time.sleep(0.05)
    ch.stop()
    assert ch.total_rx == 2


# --- Concurrent read/write ---


def test_concurrent_read_and_enqueue():
    ch, ser = _make_channel(poll_interval=0.001)
    ser.in_waiting = 0
    ch.start()
    read_results = []
    errors = []

    def reader():
        for _ in range(50):
            ch.read(10)

    def writer():
        for i in range(50):
            try:
                ch.tx_enqueue(bytes([i & 0xFF]))
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=reader), threading.Thread(target=writer)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)
    ch.stop()
    assert not errors


def test_concurrent_read_all_and_poll():
    ch, ser = _make_channel(poll_interval=0.001)
    call_count = 0

    def fake_in_waiting():
        nonlocal call_count
        call_count += 1
        return 3 if call_count % 2 == 1 else 0

    def fake_read(n):
        return b"\x01\x02\x03"

    type(ser).in_waiting = property(lambda self: fake_in_waiting())
    ser.read.side_effect = fake_read
    ch.start()
    time.sleep(0.05)
    data = ch.read_all()
    ch.stop()
    assert len(data) >= 3


# --- Drain TX write failure recovery ---


def test_drain_tx_failure_restores_data_and_sets_error():
    ch, ser = _make_channel(poll_interval=0.001)
    ser.write.side_effect = Exception("hardware error")
    ch.tx_enqueue(b"\xAA\xBB\xCC")
    ch.start()
    time.sleep(0.05)
    ch.stop()
    assert ch.tx_pending == 3
    assert ch._write_error is not None
    assert "hardware error" in str(ch._write_error)


def test_drain_tx_failure_then_recovery():
    ch, ser = _make_channel(poll_interval=0.001)
    call_count = 0

    def flaky_write(data):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("transient error")
        return len(data)

    ser.write.side_effect = flaky_write
    ch.tx_enqueue(b"\xAA\xBB")
    ch.start()
    time.sleep(0.1)
    ch.stop()
    assert ch.tx_pending == 0
    assert ch.total_tx == 2


# --- High-frequency write error isolation ---


def test_write_error_does_not_leak_between_calls():
    ch, ser = _make_channel(poll_interval=0.001)
    call_count = 0

    def flaky_write(data):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("first write fails")
        return len(data)

    ser.write.side_effect = flaky_write
    ch.tx_enqueue(b"\x01")
    ch.start()
    time.sleep(0.05)

    ch.tx_enqueue(b"\x02")
    time.sleep(0.05)
    ch.stop()
    assert ch.tx_pending == 0
    assert ch.total_tx == 2
    assert ch._write_error is None


def test_concurrent_writers_backpressure():
    ch, ser = _make_channel(tx_maxlen=16, poll_interval=0.001, write_timeout=2.0)
    ser.write.return_value = 2
    ch.start()
    errors = []

    def enqueuer(data):
        try:
            ch.tx_enqueue(data)
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=enqueuer, args=(b"\x01\x02",)),
        threading.Thread(target=enqueuer, args=(b"\x03\x04",)),
        threading.Thread(target=enqueuer, args=(b"\x05\x06",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)
    ch.flush()
    ch.stop()
    assert not errors
    assert ch.total_tx == 6


def test_write_concurrent_with_flush():
    ch, ser = _make_channel(tx_maxlen=16, poll_interval=0.001, write_timeout=2.0)
    ser.write.return_value = 2
    ch.start()
    errors = []

    def writer():
        try:
            for i in range(5):
                ch.tx_enqueue(bytes([i]))
        except Exception as e:
            errors.append(e)

    def flusher():
        for _ in range(3):
            time.sleep(0.01)
            ch.flush()

    t1 = threading.Thread(target=writer)
    t2 = threading.Thread(target=flusher)
    t1.start()
    t2.start()
    t1.join(timeout=5.0)
    t2.join(timeout=5.0)
    ch.flush()
    ch.stop()
    assert not errors
    assert ch.tx_pending == 0


def test_concurrent_write_lock_serializes():
    ch, ser = _make_channel(tx_maxlen=1024, poll_interval=0.001, write_timeout=2.0)
    ser.write.return_value = 1
    ch.start()
    write_order = []
    errors = []

    def writer(tag):
        try:
            ch.write(tag)
            write_order.append(tag)
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=writer, args=(b"A",)),
        threading.Thread(target=writer, args=(b"B",)),
        threading.Thread(target=writer, args=(b"C",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)
    ch.stop()
    assert not errors
    assert ch.total_tx == 3
    assert len(write_order) == 3


def test_concurrent_read_lock():
    ch, _ = _make_channel()
    for i in range(10):
        ch._rx.append(bytes([i]))
    results = []

    def reader():
        data = ch.read(5)
        results.append(data)

    threads = [threading.Thread(target=reader) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)
    total = sum(len(r) for r in results)
    assert total == 10
