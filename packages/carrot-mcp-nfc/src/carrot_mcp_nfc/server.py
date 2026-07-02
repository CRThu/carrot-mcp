"""Carrot MCP NFC Server - nfcscript wrapper"""

import atexit
import sys
import time
from collections import deque
from importlib.metadata import version as pkg_version

import nfc
from loguru import logger
from mcp.server.fastmcp import FastMCP
from nfctester.drivers.card_reader import CardInfo
from nfctester.registry import CardReaderRegistry, TransportRegistry

mcp = FastMCP("carrot-mcp-nfc")

_trace_buffer: deque[dict] = deque(maxlen=500)
_trace_sink_id: int | None = None


def _cleanup():
    global _trace_sink_id
    try:
        nfc.close()
    except Exception:
        pass
    _remove_trace_sink()


def _not_connected() -> dict:
    return {"status": "error", "message": "NFC reader not connected. Call connect() first."}


def _is_connected() -> bool:
    try:
        nfc.get_reader()
        return True
    except Exception:
        return False


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
    if _is_connected():
        return {"status": "ok", "message": "Already connected"}

    try:
        nfc.connect(port=port, reader_type=reader_type)
        _setup_trace_sink()
        return {"status": "ok", "port": port, "reader_type": reader_type, "transport": transport}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def disconnect() -> dict:
    """Disconnect from the NFC reader.

    Returns:
        {status}
    """
    if not _is_connected():
        return {"status": "error", "message": "Not connected"}

    try:
        nfc.close()
    except Exception:
        pass
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
    if not _is_connected():
        return _not_connected()

    try:
        if low_level:
            card_info = _low_level_find()
        else:
            card_info = nfc.active()

        if card_info is None:
            return {"status": "error", "message": "No card found"}

        return {
            "status": "ok",
            "uid": card_info.uid.hex().upper(),
            "atq": card_info.atq.hex().upper(),
            "sak": hex(card_info.sak),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _low_level_find():
    reader = nfc.get_reader()

    res_reqa = nfc.reqa()
    if not res_reqa or res_reqa.data is None:
        return None
    atq = res_reqa.data

    full_uid = []
    sak = 0
    for cl in [1, 2, 3]:
        res = nfc.anticoll(cl_level=cl, nvb=0x20)
        if not res or res.data is None:
            return None

        data = res.data
        has_next = (data[0] == 0x88)
        uid_to_select = list(data[0:5])
        sak_res = nfc.select(cl_level=cl, uid=uid_to_select)

        if has_next:
            full_uid.extend(data[1:4])
        else:
            full_uid.extend(data[0:4])
            sak = sak_res[0] if sak_res else 0
            break

    return CardInfo(uid=bytes(full_uid), atq=bytes(atq), sak=sak)


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
    if not _is_connected():
        return _not_connected()

    try:
        raw = bytes.fromhex(data)
    except ValueError:
        return {"status": "error", "message": "Invalid hex string"}

    try:
        if last_tx_bits != 0:
            res = nfc.transceive_bits(list(raw), last_tx_bits=last_tx_bits, tx_crc=tx_crc, rx_crc=rx_crc)
        else:
            res = nfc.get_reader().transceive(raw, tx_crc=tx_crc, rx_crc=rx_crc)

        if res is None or res.data is None:
            return {"status": "error", "message": "No response from card"}
        return {
            "status": "ok",
            "data": res.data.hex().upper(),
            "length": len(res.data),
            "last_rx_bits": res.rx_bits,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def reqa() -> dict:
    """Send ISO14443-A REQA (7-bit short frame).

    Returns:
        {status, data, length} or {status, message} on error
    """
    if not _is_connected():
        return _not_connected()

    try:
        res = nfc.reqa()
        if res is None or res.data is None:
            return {"status": "error", "message": "No response"}
        return {
            "status": "ok",
            "data": res.data.hex().upper(),
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
    if not _is_connected():
        return _not_connected()

    try:
        res = nfc.wupa()
        if res is None or res.data is None:
            return {"status": "error", "message": "No response"}
        return {
            "status": "ok",
            "data": res.data.hex().upper(),
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
    if not _is_connected():
        return _not_connected()

    try:
        nfc.halt()
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
    if not _is_connected():
        return _not_connected()

    try:
        uid_bytes = bytes.fromhex(uid)
    except ValueError:
        return {"status": "error", "message": "Invalid hex string"}

    try:
        res = nfc.select(cl_level=cl_level, uid=list(uid_bytes))
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
    if not _is_connected():
        return _not_connected()

    try:
        prefix = list(bytes.fromhex(uid_prefix)) if uid_prefix else []
    except ValueError:
        return {"status": "error", "message": "Invalid hex string"}

    try:
        res = nfc.anticoll(cl_level=cl_level, nvb=nvb, uid_prefix=prefix)
        if res is None or res.data is None:
            return {"status": "error", "message": "No response"}
        return {
            "status": "ok",
            "data": res.data.hex().upper(),
            "bits": res.rx_bits,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def field_on() -> dict:
    """Turn on the RF field.

    Returns:
        {status}
    """
    if not _is_connected():
        return _not_connected()
    try:
        nfc.field_on()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def field_off() -> dict:
    """Turn off the RF field.

    Returns:
        {status}
    """
    if not _is_connected():
        return _not_connected()
    try:
        nfc.field_off()
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


def _apply_expect(result: dict, args: dict, data_hex: str) -> dict:
    expect = args.get("expect")
    expect_bits = args.get("expect_bits")

    if expect is None and expect_bits is None:
        return result

    if expect is not None:
        actual_bytes = bytes.fromhex(data_hex)
        expected_bytes = bytes.fromhex(expect)

        if expect_bits is not None and len(actual_bytes) > 0:
            mask = (1 << expect_bits) - 1
            actual_list = list(actual_bytes)
            actual_list[-1] = actual_list[-1] & mask
            matched = actual_list == list(expected_bytes)
        else:
            matched = data_hex.upper() == expect.upper()
    else:
        matched = True

    if matched:
        result["matched"] = True
    else:
        result["matched"] = False
        if expect is not None:
            result["expected"] = expect
        if expect_bits is not None:
            result["expect_bits"] = expect_bits
        if args.get("on_mismatch", "stop") == "stop":
            result["status"] = "error"
            result["message"] = f"Expect mismatch: expected {expect}"
    return result


def _script_op_transceive(step: int, args: dict) -> dict:
    try:
        raw = bytes.fromhex(args.get("data", ""))
    except ValueError:
        return {"op": "transceive", "step": step, "status": "error", "message": "Invalid hex string"}
    tx_crc = args.get("tx_crc", True)
    rx_crc = args.get("rx_crc", True)
    last_tx_bits = args.get("last_tx_bits", 0)

    if last_tx_bits != 0:
        res = nfc.transceive_bits(list(raw), last_tx_bits=last_tx_bits, tx_crc=tx_crc, rx_crc=rx_crc)
    else:
        res = nfc.get_reader().transceive(raw, tx_crc=tx_crc, rx_crc=rx_crc)

    if res is None or res.data is None:
        return {"op": "transceive", "step": step, "status": "error", "message": "No response"}

    result = {
        "op": "transceive",
        "step": step,
        "status": "ok",
        "data": res.data.hex().upper(),
        "length": len(res.data),
        "last_rx_bits": res.rx_bits,
    }

    return _apply_expect(result, args, res.data.hex().upper())


def _script_op_find(step: int, args: dict) -> dict:
    low_level = args.get("low_level", False)
    if low_level:
        card_info = _low_level_find()
    else:
        card_info = nfc.active()

    if card_info is None:
        return {"op": "find", "step": step, "status": "error", "message": "No card found"}

    result = {
        "op": "find",
        "step": step,
        "status": "ok",
        "uid": card_info.uid.hex().upper(),
        "atq": card_info.atq.hex().upper(),
        "sak": hex(card_info.sak),
    }

    return _apply_expect(result, args, card_info.uid.hex().upper())


def _script_op_reqa(step: int, args: dict) -> dict:
    res = nfc.reqa()
    if res is None or res.data is None:
        return {"op": "reqa", "step": step, "status": "error", "message": "No response"}
    result = {
        "op": "reqa",
        "step": step,
        "status": "ok",
        "data": res.data.hex().upper(),
        "length": len(res.data),
    }
    return _apply_expect(result, args, res.data.hex().upper())


def _script_op_wupa(step: int, args: dict) -> dict:
    res = nfc.wupa()
    if res is None or res.data is None:
        return {"op": "wupa", "step": step, "status": "error", "message": "No response"}
    result = {
        "op": "wupa",
        "step": step,
        "status": "ok",
        "data": res.data.hex().upper(),
        "length": len(res.data),
    }
    return _apply_expect(result, args, res.data.hex().upper())


def _script_op_halt(step: int, args: dict) -> dict:
    nfc.halt()
    return {"op": "halt", "step": step, "status": "ok"}


def _script_op_select(step: int, args: dict) -> dict:
    try:
        uid_bytes = bytes.fromhex(args.get("uid", ""))
    except ValueError:
        return {"op": "select", "step": step, "status": "error", "message": "Invalid hex string"}
    cl_level = args.get("cl_level", 1)

    res = nfc.select(cl_level=cl_level, uid=list(uid_bytes))
    if res is None:
        return {"op": "select", "step": step, "status": "error", "message": "No response"}
    result = {
        "op": "select",
        "step": step,
        "status": "ok",
        "data": bytes(res).hex().upper(),
    }
    return _apply_expect(result, args, bytes(res).hex().upper())


def _script_op_anticoll(step: int, args: dict) -> dict:
    cl_level = args.get("cl_level", 1)
    nvb = args.get("nvb", 0x20)
    uid_prefix_hex = args.get("uid_prefix", "")
    try:
        prefix = list(bytes.fromhex(uid_prefix_hex)) if uid_prefix_hex else []
    except ValueError:
        return {"op": "anticoll", "step": step, "status": "error", "message": "Invalid hex string"}

    res = nfc.anticoll(cl_level=cl_level, nvb=nvb, uid_prefix=prefix)
    if res is None or res.data is None:
        return {"op": "anticoll", "step": step, "status": "error", "message": "No response"}
    result = {
        "op": "anticoll",
        "step": step,
        "status": "ok",
        "data": res.data.hex().upper(),
        "bits": res.rx_bits,
    }
    return _apply_expect(result, args, res.data.hex().upper())


def _script_op_field_on(step: int, args: dict) -> dict:
    nfc.field_on()
    return {"op": "field_on", "step": step, "status": "ok"}


def _script_op_field_off(step: int, args: dict) -> dict:
    nfc.field_off()
    return {"op": "field_off", "step": step, "status": "ok"}


def _script_op_wait(step: int, args: dict) -> dict:
    ms = args.get("ms", 0)
    time.sleep(ms / 1000.0)
    return {"op": "wait", "step": step, "status": "ok", "ms": ms}


_SCRIPT_OPS = {
    "transceive": _script_op_transceive,
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
            - {"op": "transceive", "data": "<hex>", "tx_crc"?: bool, "rx_crc"?: bool, "last_tx_bits"?: int, "expect"?: "<hex>", "expect_bits"?: int, "on_mismatch"?: "stop"|"continue"}
            - {"op": "find", "low_level"?: bool, "expect"?: "<hex>", "expect_bits"?: int, "on_mismatch"?: "stop"|"continue"}
            - {"op": "reqa", "expect"?: "<hex>", "expect_bits"?: int, "on_mismatch"?: "stop"|"continue"}
            - {"op": "wupa", "expect"?: "<hex>", "expect_bits"?: int, "on_mismatch"?: "stop"|"continue"}
            - {"op": "halt"}
            - {"op": "select", "cl_level": int, "uid": "<hex>", "expect"?: "<hex>", "expect_bits"?: int, "on_mismatch"?: "stop"|"continue"}
            - {"op": "anticoll", "cl_level"?: int, "nvb"?: int, "uid_prefix"?: "<hex>", "expect"?: "<hex>", "expect_bits"?: int, "on_mismatch"?: "stop"|"continue"}
            - {"op": "field_on"}
            - {"op": "field_off"}
            - {"op": "wait", "ms": int}

        Data ops (transceive, find, reqa, wupa, select, anticoll) support:
            - expect: Expected hex data for response matching (case-insensitive)
            - expect_bits: Number of valid bits in the last byte (1-8). Only the lower N
              bits of the last byte are compared; upper bits are treated as 0.
              Useful for 4-bit ACK/NAK responses (e.g. expect="0A", expect_bits=4).
            - on_mismatch: "stop" (default) stops script on mismatch, "continue" logs mismatch but continues

    Returns:
        List of step results. Each result contains:
        - op: Operation type
        - step: Step index (0-based)
        - status: "ok" or "error"
        - For transceive: {data, length, last_rx_bits}
        - For find: {uid, atq, sak}
        - For reqa/wupa: {data, length}
        - For select: {data}
        - For anticoll: {data, bits}
        - For wait: {ms}
        - When expect provided: {matched: bool, expected?: str}
        Stops on first error or expect mismatch (when on_mismatch="stop").
    """
    if not _is_connected():
        return [{"op": "script", "status": "error", "message": "NFC reader not connected"}]

    results = []
    for i, step in enumerate(steps):
        op = step.get("op")
        handler = _SCRIPT_OPS.get(op)
        if handler is None:
            results.append({"op": op, "step": i, "status": "error", "message": f"Unknown op: {op}"})
            break

        try:
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
