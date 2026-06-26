"""Carrot MCP Serial Server - pyserial wrapper"""

import sys
from importlib.metadata import version as pkg_version
from typing import Optional

import serial
import serial.tools.list_ports
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("carrot-mcp-serial")

_ports: dict[str, serial.Serial] = {}


def _to_hex(data: bytes) -> str:
    return data.hex().upper()


def _to_ascii(data: bytes) -> str:
    return repr(data.decode("ascii", errors="replace"))


def _decode(data: bytes, fmt: str) -> dict:
    result: dict = {"length": len(data)}
    if fmt == "hex":
        result["data_hex"] = _to_hex(data)
    elif fmt == "ascii":
        result["data_ascii"] = _to_ascii(data)
    else:
        result["data_hex"] = _to_hex(data)
        result["data_ascii"] = _to_ascii(data)
    return result


def _get_port(port: str) -> serial.Serial | None:
    ser = _ports.get(port)
    if ser is None:
        return None
    if not ser.is_open:
        _ports.pop(port, None)
        return None
    return ser


@mcp.tool()
def version() -> dict:
    """Get server version info.

    Returns:
        {status, name, version}
    """
    return {
        "status": "ok",
        "name": "carrot-mcp-serial",
        "version": pkg_version("carrot-mcp-serial"),
    }


@mcp.tool()
def list() -> list[dict[str, str]]:
    """List available serial ports.

    Returns:
        List of {port, description, hwid}
    """
    try:
        ports = serial.tools.list_ports.comports()
    except Exception as e:
        return [{"status": "error", "message": str(e)}]
    return [
        {
            "port": p.device,
            "description": p.description,
            "hwid": p.hwid,
        }
        for p in ports
    ]


@mcp.tool()
def open(
    port: str,
    baudrate: int = 115200,
    bytesize: int = 8,
    parity: str = "N",
    stopbits: float = 1,
    read_timeout: float = 1.0,
    write_timeout: float = 1.0,
) -> dict:
    """Open a serial port connection.

    Args:
        port: Serial port name (e.g. COM3, /dev/ttyUSB0)
        baudrate: Baud rate (default 115200)
        bytesize: Data bits (5, 6, 7, or 8)
        parity: Parity (N, E, O, M, S)
        stopbits: Stop bits (1, 1.5, or 2)
        read_timeout: Read timeout in seconds
        write_timeout: Write timeout in seconds

    Returns:
        {status, port, baudrate} or {status, message} on error
    """
    existing = _get_port(port)
    if existing:
        return {"status": "ok", "message": f"{port} is already open"}

    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
            timeout=read_timeout,
            write_timeout=write_timeout,
        )
        _ports[port] = ser
        return {"status": "ok", "port": port, "baudrate": baudrate}
    except serial.SerialException as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def close(port: str) -> dict:
    """Close a serial port connection.

    Returns:
        {status, port}
    """
    ser = _ports.pop(port, None)
    if ser is None:
        return {"status": "error", "message": f"{port} is not open"}
    try:
        ser.close()
    except Exception:
        pass
    return {"status": "ok", "port": port}


@mcp.tool()
def read(port: str, size: int = 256, fmt: str = "both", timeout: Optional[float] = None) -> dict:
    """Read data from an open serial port. Blocks until data available or timeout.

    Args:
        port: Serial port name
        size: Max bytes to read (default 256)
        fmt: Output format - "hex", "ascii", or "both" (default).
            ascii output escapes non-printable chars (e.g. \\n, \\x00)
        timeout: Override read timeout in seconds (optional)

    Returns:
        {status, length, data_hex?, data_ascii?}
    """
    ser = _get_port(port)
    if ser is None:
        return {"status": "error", "message": f"{port} is not open"}

    try:
        old_timeout = ser.timeout
        if timeout is not None:
            ser.timeout = timeout
        data = ser.read(size)
        if timeout is not None:
            ser.timeout = old_timeout
        if not data:
            result = _decode(b"", fmt)
            result["status"] = "ok"
            return result
        result = _decode(data, fmt)
        result["status"] = "ok"
        return result
    except serial.SerialException as e:
        _ports.pop(port, None)
        return {"status": "error", "message": str(e)}


@mcp.tool()
def recv(port: str, size: Optional[int] = None, fmt: str = "both") -> dict:
    """Non-blocking read. Returns whatever is available in the buffer right now.

    Args:
        port: Serial port name
        size: Max bytes to read (default: all available)
        fmt: Output format - "hex", "ascii", or "both" (default).
            ascii output escapes non-printable chars (e.g. \\n, \\x00)

    Returns:
        {status, length, data_hex?, data_ascii?}
    """
    ser = _get_port(port)
    if ser is None:
        return {"status": "error", "message": f"{port} is not open"}

    try:
        n = size if size is not None else ser.in_waiting
        data = ser.read(n) if n > 0 else b""
        if not data:
            result = _decode(b"", fmt)
            result["status"] = "ok"
            return result
        result = _decode(data, fmt)
        result["status"] = "ok"
        return result
    except serial.SerialException as e:
        _ports.pop(port, None)
        return {"status": "error", "message": str(e)}


@mcp.tool()
def write(port: str, hex: Optional[str] = None, ascii: Optional[str] = None) -> dict:
    """Write data to an open serial port. Provide hex or ascii.

    Args:
        port: Serial port name
        hex: Hex string, e.g. "48656C6C6F"
        ascii: ASCII string with escape support, e.g. "Hello\\nWorld", "\\x00\\x01"

    Returns:
        {status, bytes_written} or {status, message} on error
    """
    ser = _get_port(port)
    if ser is None:
        return {"status": "error", "message": f"{port} is not open"}

    if hex and ascii:
        return {"status": "error", "message": "Provide only one of hex or ascii"}

    if hex:
        try:
            raw = bytes.fromhex(hex)
        except ValueError:
            return {"status": "error", "message": "Invalid hex string"}
    elif ascii:
        try:
            raw = ascii.encode("ascii").decode("unicode_escape").encode("raw_unicode_escape")
        except (ValueError, UnicodeDecodeError):
            return {"status": "error", "message": "Invalid ascii string"}
    else:
        return {"status": "error", "message": "Provide hex or ascii"}

    try:
        written = ser.write(raw)
        return {"status": "ok", "bytes_written": written}
    except serial.SerialTimeoutException:
        return {"status": "error", "message": "Write timed out"}
    except serial.SerialException as e:
        _ports.pop(port, None)
        return {"status": "error", "message": str(e)}


def main():
    print("carrot-mcp-serial server ready", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
