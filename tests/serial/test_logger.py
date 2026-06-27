"""Tests for HistoryLogger."""

from carrot_mcp_serial.channel import ChannelEvent
from carrot_mcp_serial.logger import HistoryLogger


def _event(op="recv", data=b"\x01", pending=0):
    return ChannelEvent(op, data, pending)


def test_on_event():
    logger = HistoryLogger()
    e = _event("write", b"\xAA", pending=5)
    logger.on_event(e)
    entries = logger.get_entries()
    assert len(entries) == 1
    assert entries[0]["op"] == "write"
    assert entries[0]["data"] == "AA"
    assert entries[0]["pending"] == 5


def test_on_event_multiple():
    logger = HistoryLogger()
    logger.on_event(_event("write", b"\x01"))
    logger.on_event(_event("recv", b"\x02"))
    logger.on_event(_event("read", b"\x03"))
    entries = logger.get_entries()
    assert len(entries) == 3
    assert [e["op"] for e in entries] == ["write", "recv", "read"]


def test_get_entries_empty():
    logger = HistoryLogger()
    assert logger.get_entries() == []


def test_get_entries_limit():
    logger = HistoryLogger()
    for i in range(10):
        logger.on_event(_event("recv", bytes([i])))
    entries = logger.get_entries(limit=3)
    assert len(entries) == 3
    assert entries[0]["data"] == "07"
    assert entries[2]["data"] == "09"


def test_get_entries_limit_larger_than_data():
    logger = HistoryLogger()
    logger.on_event(_event("recv", b"\x01"))
    entries = logger.get_entries(limit=100)
    assert len(entries) == 1


def test_get_entries_no_limit():
    logger = HistoryLogger()
    for i in range(5):
        logger.on_event(_event("recv", bytes([i])))
    entries = logger.get_entries()
    assert len(entries) == 5


def test_max_entries_overflow():
    logger = HistoryLogger(max_entries=3)
    for i in range(5):
        logger.on_event(_event("recv", bytes([i])))
    entries = logger.get_entries()
    assert len(entries) == 3
    assert entries[0]["data"] == "02"
    assert entries[2]["data"] == "04"


def test_clear():
    logger = HistoryLogger()
    logger.on_event(_event("recv", b"\x01"))
    logger.on_event(_event("write", b"\x02"))
    assert len(logger.get_entries()) == 2
    logger.clear()
    assert len(logger.get_entries()) == 0


def test_event_to_dict_format():
    logger = HistoryLogger()
    e = _event("write", b"\xAB\xCD", pending=10)
    logger.on_event(e)
    entry = logger.get_entries()[0]
    assert entry["ts"] > 0
    assert entry["op"] == "write"
    assert entry["data"] == "ABCD"
    assert entry["length"] == 2
    assert entry["pending"] == 10


def test_max_entries_one():
    logger = HistoryLogger(max_entries=1)
    logger.on_event(_event("recv", b"\x01"))
    logger.on_event(_event("recv", b"\x02"))
    entries = logger.get_entries()
    assert len(entries) == 1
    assert entries[0]["data"] == "02"
