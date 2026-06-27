"""Carrot MCP NFC Server - nfcscript wrapper"""

import atexit
import sys
import time
from collections import deque
from importlib.metadata import version as pkg_version

from loguru import logger
from mcp.server.fastmcp import FastMCP
from nfctester.registry import CardReaderRegistry, TransportRegistry

mcp = FastMCP("carrot-mcp-nfc")

_reader = None
_connected = False

_trace_buffer: deque[dict] = deque(maxlen=500)
_trace_sink_id: int | None = None


def _cleanup():
    global _reader, _connected, _trace_sink_id
    if _connected and _reader is not None:
        try:
            _reader.disconnect()
        except Exception:
            pass
    _reader = None
    _connected = False
    _remove_trace_sink()


def _not_connected() -> dict:
    return {"status": "error", "message": "NFC reader not connected. Call connect() first."}


def _setup_trace_sink():
    global _trace_sink_id
    _remove_trace_sink()

    def _sink(message):
        record = message.record
        entry = {
            "time": record["time"].strftime("%H:%M:%S.%f")[:-3],
            "level": record["level"].name,
            "layer": record["extra"].get("layer", ""),
            "message": str(record["message"]),
        }
        _trace_buffer.append(entry)

    _trace_sink_id = logger.add(_sink, level=0, format="{message}")


def _remove_trace_sink():
    global _trace_sink_id
    if _trace_sink_id is not None:
        try:
            logger.remove(_trace_sink_id)
        except Exception:
            pass
        _trace_sink_id = None


@mcp.tool()
def version() -> dict:
    """Get server version info.

    Returns:
        {status, name, version}
    """
    return {
        "status": "ok",
        "name": "carrot-mcp-nfc",
        "version": pkg_version("carrot-mcp-nfc"),
    }


@mcp.tool()
def list_readers() -> dict:
    """List available reader types and transport types.

    Returns:
        {status, readers, transports}
    """
    try:
        return {
            "status": "ok",
            "readers": CardReaderRegistry.list(),
            "transports": TransportRegistry.list(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def connect(port: str, reader_type: str = "pn532", transport: str = "serial") -> dict:
    """Connect to an NFC reader.

    Args:
        port: Serial port name (e.g. COM20, /dev/ttyUSB0)
        reader_type: Reader type (default "pn532"). Use list_readers to see available types.
        transport: Transport type (default "serial"). Use list_readers to see available types.

    Returns:
        {status, port, reader_type, transport} or {status, message} on error
    """
    global _reader, _connected

    if _connected:
        return {"status": "ok", "message": "Already connected"}

    try:
        _reader = CardReaderRegistry.create(reader_type, transport=transport, port=port)
        _reader.connect()
        _connected = True
        _setup_trace_sink()
        return {"status": "ok", "port": port, "reader_type": reader_type, "transport": transport}
    except Exception as e:
        _reader = None
        _connected = False
        return {"status": "error", "message": str(e)}


@mcp.tool()
def disconnect() -> dict:
    """Disconnect from the NFC reader.

    Returns:
        {status}
    """
    global _reader, _connected
    if not _connected:
        return {"status": "error", "message": "Not connected"}

    try:
        _reader.disconnect()
    except Exception:
        pass
    _reader = None
    _connected = False
    _remove_trace_sink()
    return {"status": "ok"}


@mcp.tool()
def find(low_level: bool = False) -> dict:
    """Find and activate an NFC card.

    Args:
        low_level: If True, use low-level anticollision for non-standard cards.

    Returns:
        {status, uid, atq, sak} or {status, message} on error
    """
    if not _connected or _reader is None:
        return _not_connected()

    try:
        if not low_level:
            card_info = _reader.find()
        else:
            card_info = _low_level_find()

        if card_info is None:
            return {"status": "error", "message": "No card found"}

        return {
            "status": "ok",
            "uid": card_info["uid"].hex().upper(),
            "atq": card_info["atq"].hex().upper(),
            "sak": hex(card_info["sak"]),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _low_level_find():
    if _reader is None:
        return None

    res_reqa = _reader.reqa()
    if not res_reqa:
        return None
    atq = res_reqa.data

    full_uid = []
    sak = 0
    for cl in [1, 2, 3]:
        res = _reader.anticoll(cl_level=cl, nvb=0x20)
        if not res or not res.data:
            return None

        data = res.data
        has_next = (data[0] == 0x88)
        uid_to_select = data[0:5]
        sak_res = _reader.select(cl_level=cl, uid=uid_to_select)

        if has_next:
            full_uid.extend(data[1:4])
        else:
            full_uid.extend(data[0:4])
            sak = sak_res[0] if sak_res else 0
            break

    return {
        "uid": bytes(full_uid),
        "atq": bytes(atq),
        "sak": sak,
    }


@mcp.tool()
def transceive(
    data: str,
    tx_crc: bool = True,
    rx_crc: bool = True,
    last_tx_bits: int = 0,
) -> dict:
    """Send raw data to the card and receive response (InCommunicateThru).

    Args:
        data: Hex string to send (e.g. "6007")
        tx_crc: Add CRC to transmitted data (default True)
        rx_crc: Verify CRC on received data (default True)
        last_tx_bits: Number of valid bits in last byte (0-7, default 0 = full byte).
                      Use for non-byte-aligned commands like REQA (7 bits).

    Returns:
        {status, data, length, last_rx_bits} or {status, message} on error
    """
    if not _connected or _reader is None:
        return _not_connected()

    try:
        raw = bytes.fromhex(data)
    except ValueError:
        return {"status": "error", "message": "Invalid hex string"}

    try:
        _reader.set_crc(tx_crc, rx_crc)
        res = _reader.transceive(raw, last_tx_bits=last_tx_bits)
        if res is None:
            return {"status": "error", "message": "No response from card"}
        return {
            "status": "ok",
            "data": res.hex().upper(),
            "length": len(res),
            "last_rx_bits": _reader.last_rx_bits,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def exchange(data: str) -> dict:
    """Send data via InDataExchange (auto CRC, target 1).

    Args:
        data: Hex string to send (e.g. "6007")

    Returns:
        {status, data, length} or {status, message} on error
    """
    if not _connected or _reader is None:
        return _not_connected()

    try:
        raw = bytes.fromhex(data)
    except ValueError:
        return {"status": "error", "message": "Invalid hex string"}

    try:
        res = _reader.exchange(raw)
        if res is None:
            return {"status": "error", "message": "No response from card"}
        return {
            "status": "ok",
            "data": res.hex().upper(),
            "length": len(res),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def reqa() -> dict:
    """Send ISO14443-A REQA (7-bit short frame).

    Returns:
        {status, data, length} or {status, message} on error
    """
    if not _connected or _reader is None:
        return _not_connected()

    try:
        res = _reader.reqa()
        if res is None:
            return {"status": "error", "message": "No response"}
        return {
            "status": "ok",
            "data": bytes(res.data).hex().upper(),
            "length": len(res.data),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def wupa() -> dict:
    """Send ISO14443-A WUPA (7-bit short frame).

    Returns:
        {status, data, length} or {status, message} on error
    """
    if not _connected or _reader is None:
        return _not_connected()

    try:
        res = _reader.wupa()
        if res is None:
            return {"status": "error", "message": "No response"}
        return {
            "status": "ok",
            "data": bytes(res.data).hex().upper(),
            "length": len(res.data),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def halt() -> dict:
    """Send ISO14443-A HALT command.

    Returns:
        {status} or {status, message} on error
    """
    if not _connected or _reader is None:
        return _not_connected()

    try:
        _reader.halt()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def select(cl_level: int, uid: str) -> dict:
    """Send ISO14443-A SELECT command.

    Args:
        cl_level: Cascade level (1, 2, or 3)
        uid: 5-byte UID with BCC as hex string (e.g. "04AABBCCDD77")

    Returns:
        {status, data} or {status, message} on error
    """
    if not _connected or _reader is None:
        return _not_connected()

    try:
        uid_bytes = bytes.fromhex(uid)
    except ValueError:
        return {"status": "error", "message": "Invalid hex string"}

    try:
        res = _reader.select(cl_level=cl_level, uid=list(uid_bytes))
        if res is None:
            return {"status": "error", "message": "No response"}
        return {
            "status": "ok",
            "data": bytes(res).hex().upper(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def anticoll(cl_level: int = 1, nvb: int = 0x20, uid_prefix: str = "") -> dict:
    """Send ISO14443-A ANTICOLL (anti-collision) command.

    Args:
        cl_level: Cascade level (1, 2, or 3)
        nvb: Number of Valid Bits (default 0x20)
        uid_prefix: Known UID prefix bytes as hex string (default empty)

    Returns:
        {status, data, bits} or {status, message} on error
    """
    if not _connected or _reader is None:
        return _not_connected()

    try:
        prefix = list(bytes.fromhex(uid_prefix)) if uid_prefix else []
    except ValueError:
        return {"status": "error", "message": "Invalid hex string"}

    try:
        res = _reader.anticoll(cl_level=cl_level, nvb=nvb, uid_prefix=prefix)
        if res is None:
            return {"status": "error", "message": "No response"}
        return {
            "status": "ok",
            "data": bytes(res.data).hex().upper(),
            "bits": res.bits,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def field_on() -> dict:
    """Turn on the RF field.

    Returns:
        {status}
    """
    if not _connected or _reader is None:
        return _not_connected()
    try:
        _reader.set_rf_field(True)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def field_off() -> dict:
    """Turn off the RF field.

    Returns:
        {status}
    """
    if not _connected or _reader is None:
        return _not_connected()
    try:
        _reader.set_rf_field(False)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def trace_get(level: str = "", layer: str = "") -> dict:
    """Get accumulated trace log entries as JSON.

    Args:
        level: Filter by log level (e.g. "DEBUG", "INFO"). Empty = all levels.
        layer: Filter by layer name (e.g. "DRIVER", "PROTOCOL"). Empty = all layers.

    Returns:
        {status, entries: [{time, level, layer, message}]}
    """
    entries = list(_trace_buffer)
    if level:
        level_upper = level.upper()
        entries = [e for e in entries if e["level"] == level_upper]
    if layer:
        layer_upper = layer.upper()
        entries = [e for e in entries if e["layer"] == layer_upper]
    return {"status": "ok", "entries": entries}


def _script_op_transceive(step: int, args: dict) -> dict:
    raw = bytes.fromhex(args.get("data", ""))
    tx_crc = args.get("tx_crc", True)
    rx_crc = args.get("rx_crc", True)
    last_tx_bits = args.get("last_tx_bits", 0)

    _reader.set_crc(tx_crc, rx_crc)
    res = _reader.transceive(raw, last_tx_bits=last_tx_bits)
    if res is None:
        return {"op": "transceive", "step": step, "status": "error", "message": "No response"}

    result = {
        "op": "transceive",
        "step": step,
        "status": "ok",
        "data": res.hex().upper(),
        "length": len(res),
        "last_rx_bits": _reader.last_rx_bits,
    }

    expect = args.get("expect")
    if expect is not None:
        expected_raw = bytes.fromhex(expect)
        if res == expected_raw:
            result["matched"] = True
        else:
            result["matched"] = False
            result["expected"] = expect
            if args.get("on_mismatch", "stop") == "stop":
                result["status"] = "error"
                result["message"] = f"Expect mismatch: expected {expect}"

    return result


def _script_op_exchange(step: int, args: dict) -> dict:
    raw = bytes.fromhex(args.get("data", ""))
    res = _reader.exchange(raw)
    if res is None:
        return {"op": "exchange", "step": step, "status": "error", "message": "No response"}

    result = {
        "op": "exchange",
        "step": step,
        "status": "ok",
        "data": res.hex().upper(),
        "length": len(res),
    }

    expect = args.get("expect")
    if expect is not None:
        expected_raw = bytes.fromhex(expect)
        if res == expected_raw:
            result["matched"] = True
        else:
            result["matched"] = False
            result["expected"] = expect
            if args.get("on_mismatch", "stop") == "stop":
                result["status"] = "error"
                result["message"] = f"Expect mismatch: expected {expect}"

    return result


def _script_op_find(step: int, args: dict) -> dict:
    low_level = args.get("low_level", False)
    if not low_level:
        card_info = _reader.find()
    else:
        card_info = _low_level_find()

    if card_info is None:
        return {"op": "find", "step": step, "status": "error", "message": "No card found"}

    return {
        "op": "find",
        "step": step,
        "status": "ok",
        "uid": card_info["uid"].hex().upper(),
        "atq": card_info["atq"].hex().upper(),
        "sak": hex(card_info["sak"]),
    }


def _script_op_reqa(step: int, args: dict) -> dict:
    res = _reader.reqa()
    if res is None:
        return {"op": "reqa", "step": step, "status": "error", "message": "No response"}
    return {
        "op": "reqa",
        "step": step,
        "status": "ok",
        "data": bytes(res.data).hex().upper(),
        "length": len(res.data),
    }


def _script_op_wupa(step: int, args: dict) -> dict:
    res = _reader.wupa()
    if res is None:
        return {"op": "wupa", "step": step, "status": "error", "message": "No response"}
    return {
        "op": "wupa",
        "step": step,
        "status": "ok",
        "data": bytes(res.data).hex().upper(),
        "length": len(res.data),
    }


def _script_op_halt(step: int, args: dict) -> dict:
    _reader.halt()
    return {"op": "halt", "step": step, "status": "ok"}


def _script_op_select(step: int, args: dict) -> dict:
    uid_bytes = bytes.fromhex(args.get("uid", ""))
    cl_level = args.get("cl_level", 1)
    res = _reader.select(cl_level=cl_level, uid=list(uid_bytes))
    if res is None:
        return {"op": "select", "step": step, "status": "error", "message": "No response"}
    return {
        "op": "select",
        "step": step,
        "status": "ok",
        "data": bytes(res).hex().upper(),
    }


def _script_op_anticoll(step: int, args: dict) -> dict:
    cl_level = args.get("cl_level", 1)
    nvb = args.get("nvb", 0x20)
    uid_prefix_hex = args.get("uid_prefix", "")
    prefix = list(bytes.fromhex(uid_prefix_hex)) if uid_prefix_hex else []

    res = _reader.anticoll(cl_level=cl_level, nvb=nvb, uid_prefix=prefix)
    if res is None:
        return {"op": "anticoll", "step": step, "status": "error", "message": "No response"}
    return {
        "op": "anticoll",
        "step": step,
        "status": "ok",
        "data": bytes(res.data).hex().upper(),
        "bits": res.bits,
    }


def _script_op_field_on(step: int, args: dict) -> dict:
    _reader.set_rf_field(True)
    return {"op": "field_on", "step": step, "status": "ok"}


def _script_op_field_off(step: int, args: dict) -> dict:
    _reader.set_rf_field(False)
    return {"op": "field_off", "step": step, "status": "ok"}


def _script_op_wait(step: int, args: dict) -> dict:
    ms = args.get("ms", 0)
    time.sleep(ms / 1000.0)
    return {"op": "wait", "step": step, "status": "ok", "ms": ms}


_HEX_OPS = frozenset({"transceive", "exchange", "select", "anticoll"})
_HEX_OPS_WITH_OPTIONAL = frozenset({"anticoll"})

_SCRIPT_OPS = {
    "transceive": _script_op_transceive,
    "exchange": _script_op_exchange,
    "find": _script_op_find,
    "reqa": _script_op_reqa,
    "wupa": _script_op_wupa,
    "halt": _script_op_halt,
    "select": _script_op_select,
    "anticoll": _script_op_anticoll,
    "field_on": _script_op_field_on,
    "field_off": _script_op_field_off,
    "wait": _script_op_wait,
}


@mcp.tool()
def script(steps: list[dict]) -> list[dict]:
    """Execute a sequence of NFC operations.

    Args:
        steps: List of operations. Each step is a dict with 'op' field:
            - transceive: {"op": "transceive", "data": "<hex>", "tx_crc"?: bool, "rx_crc"?: bool, "last_tx_bits"?: int}
            - exchange: {"op": "exchange", "data": "<hex>"}
            - find: {"op": "find", "low_level"?: bool}
            - reqa: {"op": "reqa"}
            - wupa: {"op": "wupa"}
            - halt: {"op": "halt"}
            - select: {"op": "select", "cl_level": int, "uid": "<hex>"}
            - anticoll: {"op": "anticoll", "cl_level"?: int, "nvb"?: int, "uid_prefix"?: "<hex>"}
            - field_on: {"op": "field_on"}
            - field_off: {"op": "field_off"}
            - wait: {"op": "wait", "ms": int}

    Returns:
        List of step results. Each result contains:
        - op: Operation type
        - step: Step index (0-based)
        - status: "ok" or "error"
        - For transceive: {data, length, last_rx_bits}
        - For exchange: {data, length}
        - For find: {uid, atq, sak}
        - For reqa/wupa: {data, length}
        - For select: {data}
        - For anticoll: {data, bits}
        - For wait: {ms}
        Stops on first error or expect mismatch.
    """
    if not _connected or _reader is None:
        return [{"op": "script", "status": "error", "message": "NFC reader not connected"}]

    results = []
    for i, step in enumerate(steps):
        op = step.get("op")
        handler = _SCRIPT_OPS.get(op)
        if handler is None:
            results.append({"op": op, "step": i, "status": "error", "message": f"Unknown op: {op}"})
            break

        try:
            if op in _HEX_OPS or (op in _HEX_OPS_WITH_OPTIONAL and step.get("uid_prefix" if op == "anticoll" else "data", "")):
                try:
                    if op == "transceive":
                        bytes.fromhex(step.get("data", ""))
                    elif op == "exchange":
                        bytes.fromhex(step.get("data", ""))
                    elif op == "select":
                        bytes.fromhex(step.get("uid", ""))
                    elif op == "anticoll" and step.get("uid_prefix", ""):
                        bytes.fromhex(step["uid_prefix"])
                except ValueError:
                    results.append({"op": op, "step": i, "status": "error", "message": "Invalid hex string"})
                    break

            result = handler(i, step)
            results.append(result)
            if result["status"] == "error":
                break

        except Exception as e:
            results.append({"op": op, "step": i, "status": "error", "message": str(e)})
            break

    return results


@mcp.tool()
def trace_clear() -> dict:
    """Clear the trace log buffer.

    Returns:
        {status}
    """
    _trace_buffer.clear()
    return {"status": "ok"}


def _shutdown_all() -> None:
    _cleanup()


def main():
    atexit.register(_shutdown_all)
    print("carrot-mcp-nfc server ready", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
