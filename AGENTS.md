# AGENTS.md

## Project Overview

Carrot MCP is a collection of MCP (Model Context Protocol) servers for hardware and data interfaces.

## Project Structure

```
carrot-mcp/
├── pyproject.toml              # Root: meta package, workspace config
├── src/carrot_mcp/             # Main package (CLI entry point)
│   ├── __init__.py
│   └── cli.py                  # carrot-mcp command
├── packages/
│   ├── carrot-mcp-ds/          # Datasheet MCP server
│   │   ├── pyproject.toml
│   │   └── src/carrot_mcp_ds/
│   ├── carrot-mcp-serial/      # Serial port MCP server
│   │   ├── pyproject.toml
│   │   └── src/carrot_mcp_serial/
│   └── carrot-mcp-nfc/         # NFC reader MCP server
│       ├── pyproject.toml
│       └── src/carrot_mcp_nfc/
└── tests/
    ├── ds/
    ├── serial/
    │   ├── test_transport.py
    │   ├── test_channel.py
    │   ├── test_logger.py
    │   └── test_server.py
    └── nfc/
```

## Build & Test Commands

```bash
# Install dependencies
uv sync --all-packages

# Run tests
uv run pytest

# Run tests for specific server
uv run pytest tests/serial/ -v

# Run single test module
uv run pytest tests/serial/test_channel.py -v

# Run servers
uv run carrot-mcp ds
uv run carrot-mcp serial
uv run carrot-mcp nfc
uv run python -m carrot_mcp_ds
```

## Code Style

- Python 3.10+
- Use type hints
- Follow existing patterns in the codebase
- Each MCP server follows the same structure: server.py with FastMCP
- All tools return dict with `{"status": "ok"|"error", ...}` format
- Each server implements a `version` tool using `importlib.metadata.version`
- Version is read from `pyproject.toml` — do NOT hardcode `__version__` in `__init__.py`
- **Test directories must NOT have `__init__.py`** — it shadows the `serial` package from pyserial
- 修改代码（函数名、工具名等）后，必须同步更新 `AGENTS.md` 和各包的 `README.md`，并运行 `uv run pytest` 验证

## Serial MCP Server Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info |
| `list_ports` | List available serial ports |
| `open` | Open a serial port (baudrate, parity, timeouts, buffer_size) |
| `close` | Close a serial port |
| `read` | Blocking read from buffer with timeout |
| `recv` | Non-blocking read from buffer (returns available data) |
| `write` | Write data (hex or ascii with escape support) |
| `script` | Execute a sequence of serial operations (write/read/wait/flush) |
| `history` | Get operation history for a port |

### Architecture

```
Application Layer (MCP tools)
    ↓ read/write (all via Channel buffers)
Channel Layer (Channel: RX/TX buffers with backpressure, Event-driven wait, observer events)
    ↓ polling via daemon thread (only thread touching hardware)
Transport Layer (Transport ABC → SerialTransport)
    ↓ raw I/O
Hardware Layer (serial.Serial)
```

**Separation of concerns (low coupling, high cohesion):**

- `transport.py`: `Transport` ABC + `SerialTransport` — pure FIFO interface (read/write/buffer-status/close), context manager support, no wait/blocking semantics
- `channel.py`: `Channel` — wraps Transport, provides RX/TX deque buffers with backpressure, independent locks (`_rx_lock` / `_tx_lock`), background polling via daemon thread + `threading.Event`, emits `ChannelEvent` to observers
- `logger.py`: `HistoryLogger` — external observer, plugs into Channel via `attach()`, records operation history independently

**Channel design:**
- RX/TX dual buffers (deque-based, configurable capacity)
- **Backpressure model**: RX full → poll thread stops reading from hardware (data stays in OS serial buffer); TX full → `tx_enqueue()` blocks until drain creates space (with `_write_timeout`)
- **Locks**:
  - `_rx_lock` — protects RX buffer reads/writes (`read`, `read_all`, `peek`, `rx_pending`, `total_rx`)
  - `_tx_lock` — protects TX buffer reads/writes (`tx_enqueue`, `tx_dequeue`, `tx_pending`, `total_tx`)
  - `_write_lock` — serializes `write()` and `flush()` calls (prevents `_drain_done` Event signal loss between concurrent callers)
- `_tx_cond` (`threading.Condition`) — TX backpressure signaling between `tx_enqueue()` and `_drain_tx()`
- All hardware I/O performed by poll thread only — callers only touch buffers (thread-safe)
- `read_timeout` / `write_timeout` are caller-provided, passed through from server (hardware-level timeouts in `serial.Serial` are hardcoded to 1.0)
- `write()` acquires `_write_lock`, enqueues to TX buffer, blocks via `Event.wait()` until drain completes
- `flush()` acquires `_write_lock`, uses event-driven wait (clear + wait on `_drain_done`), not polling
- `wait_read()` uses `_rx_lock` to protect `_data_ready.clear()` from signal loss
- `_emit()` called **outside** locks to prevent observer deadlock
- Poll thread is daemon — process exits cleanly without explicit `stop()`
- TX/RX cumulative byte counters (`total_tx` / `total_rx`) — read under respective locks
- Observer pattern: `attach(observer)` / `detach(observer)`, observers receive `ChannelEvent`
- Channel never knows about history/logging — that's the observer's job

**Server resource management:**
- `_cleanup_channel(port)`: centralized cleanup — close channel, remove from registry (safe to call multiple times)
- `_shutdown_all()` registered via `atexit` — closes all open channels on server exit
- All exception handlers call `_cleanup_channel()` instead of ad-hoc pop

### Script Tool Details

`script` supports sequential operations with `fmt` as top-level param (shared by all steps).

Read step params (all optional):
- `size`: Max bytes to read (default 256)
- `timeout`: Read timeout in seconds (default 1.0)
- `expect`: Expected data for matching (default None)
- `on_mismatch`: "stop" (default) or "continue" - controls script behavior on expect mismatch

Example:
```json
[
  {"op": "write", "data": "AA"},
  {"op": "read", "size": 256, "timeout": 1.0, "expect": "BB", "on_mismatch": "stop"}
]
```

## Adding a New MCP Server

1. Create directory: `packages/carrot-mcp-<name>/`
2. Add `pyproject.toml` with mcp dependency, scripts entry, and entry point:
   ```toml
   [project.scripts]
   carrot-mcp-<name> = "carrot_mcp_<name>.server:main"

   [project.entry-points."carrot_mcp.servers"]
   <name> = "carrot_mcp_<name>.server:mcp"
   ```
3. Create `src/carrot_mcp_<name>/server.py` with FastMCP
4. Create `src/carrot_mcp_<name>/__main__.py` (allows `python -m carrot_mcp_<name>`)
5. Add `version` tool using `importlib.metadata.version`
6. Add to root `pyproject.toml` dependencies and uv.sources
7. Write tests in `tests/<name>/`

CLI auto-discovers servers via entry points - no need to update cli.py.

## License

Apache 2.0
