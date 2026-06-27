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
│   ├── carrot-mcp-pdf/         # PDF MCP server
│   │   ├── pyproject.toml
│   │   └── src/carrot_mcp_pdf/
│   ├── carrot-mcp-office/      # Office MCP server
│   │   ├── pyproject.toml
│   │   └── src/carrot_mcp_office/
│   ├── carrot-mcp-serial/      # Serial port MCP server
│   │   ├── pyproject.toml
│   │   └── src/carrot_mcp_serial/
│   └── carrot-mcp-nfc/         # NFC reader MCP server
│       ├── pyproject.toml
│       └── src/carrot_mcp_nfc/
└── tests/
    ├── pdf/
    ├── office/
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
uv run carrot-mcp pdf
uv run carrot-mcp office
uv run carrot-mcp serial
uv run carrot-mcp nfc
uv run python -m carrot_mcp_pdf
uv run python -m carrot_mcp_office
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
- `write()` acquires `_write_lock`, enqueues to TX buffer, blocks via `Event.wait()` until drain completes; raises `TimeoutError` if drain does not finish within `write_timeout`, raises the original exception on hardware write failure
- `flush()` acquires `_write_lock`, uses event-driven wait (clear + wait on `_drain_done`), not polling
- `wait_read()` uses `_rx_lock` to protect `_data_ready.clear()` from signal loss
- `_emit()` called **outside** locks to prevent observer deadlock
- Poll thread is daemon — process exits cleanly without explicit `stop()`
- TX/RX cumulative byte counters (`total_tx` / `total_rx`) — read under respective locks
- Observer pattern: `attach(observer)` / `detach(observer)` — detach is no-op if observer not attached
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

## NFC MCP Server Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info |
| `list_readers` | List available reader types and transports |
| `connect` | Connect to NFC reader (port, reader_type, transport) |
| `disconnect` | Disconnect from reader |
| `find` | Find and activate an NFC card (returns uid, atq, sak) |
| `transceive` | Raw frame exchange with bit-level control (InCommunicateThru) |
| `exchange` | Data exchange with auto CRC (InDataExchange) |
| `reqa` | ISO14443-A REQA (7-bit short frame) |
| `wupa` | ISO14443-A WUPA (7-bit short frame) |
| `halt` | ISO14443-A HALT |
| `select` | ISO14443-A SELECT |
| `anticoll` | ISO14443-A ANTICOLL (anti-collision) |
| `field_on` | Turn on RF field |
| `field_off` | Turn off RF field |
| `script` | Execute a sequence of NFC operations (supports `expect`/`on_mismatch` matching) |
| `trace_get` | Get trace log entries (supports level/layer filtering) |
| `trace_clear` | Clear trace log buffer |

### Architecture

```
Application Layer (MCP tools)
    ↓ connect/find/transceive/reqa/etc
Wrapper Layer (server.py - state management, error handling, trace capture)
    ↓ imports nfctester registries
Library Layer (nfctester registries)
    ├─ CardReaderRegistry: pn532, clrc663
    ├─ TransportRegistry: serial
    └─ trace: loguru sink → JSON buffer
Hardware Layer (PN532 / CLRC663 via serial)
```

- Wraps `nfctester` registry system (CardReaderRegistry, TransportRegistry)
- Single reader session managed via module-level `_reader` / `_connected` state
- `_cleanup()` registered via `atexit` for safe shutdown
- `find()` supports both high-level (`reader.find()`) and low-level (manual anticollision) modes
- `find(low_level=True)` performs multi-cascade anticollision with per-step exception handling
- `transceive()` exposes `last_tx_bits` for non-byte-aligned commands (e.g. REQA 7 bits)
- `exchange()` uses InDataExchange with auto CRC (simpler for card-level operations)
- `script` hex validation is done inside each handler (consistent "Invalid hex string" errors); no pre-validation layer
- Trace output captured via loguru sink, returned as JSON via `trace_get()`

## Office MCP Server Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info |
| `workbook_metadata` | Get workbook metadata (sheet names, properties) |
| `workbook_search` | Search for values in a sheet |
| `create_sheet` | Create a new sheet (creates workbook if needed) |
| `rename_sheet` | Rename a sheet |
| `delete_sheet` | Delete a sheet |
| `insert_rows` | Insert rows into a sheet |
| `delete_rows` | Delete rows from a sheet |
| `insert_columns` | Insert columns into a sheet |
| `delete_columns` | Delete columns from a sheet |
| `read_range` | Read cell values from a range |
| `write_range` | Write a 2D array to a range (supports formulas) |
| `copy_range` | Copy a range to another location |
| `delete_range` | Clear cell contents in a range |
| `read_chart` | Read chart information from a sheet |
| `write_chart` | Create a chart (bar, line, pie, scatter) |
| `format_range` | Format cells (font, color, alignment, merge/unmerge) |
| `inspect` | Inspect document structure (paragraphs, tables, images) |
| `insert_para` | Insert a paragraph |
| `modify_para` | Modify paragraph text |
| `format_para` | Format a paragraph (style, alignment, font) |
| `delete_para` | Delete a paragraph |
| `insert_table` | Insert a table with optional data |
| `modify_table` | Modify a table cell |
| `format_table` | Apply a table style |
| `delete_table` | Delete a table |
| `insert_image` | Insert an image |
| `delete_image` | Delete an inline image |

### Architecture

```
Application Layer (MCP tools)
    ↓ workbook/doc operations via openpyxl / python-docx
Library Layer (openpyxl, python-docx)
    ↓ stateless per-call: open → operate → save → close
File Layer (.xlsx, .docx)
```

- Stateless per-call pattern: each tool opens file, performs operation, saves, closes
- `create_sheet` creates workbook if file doesn't exist; other Excel tools require existing file
- `insert_para` / `insert_table` / `insert_image` create document if file doesn't exist
- Split modules: `excel.py` (16 tools), `word.py` (11 tools), shared `_mcp.py` FastMCP instance
- Word insert-by-index uses XML manipulation (`_element.addprevious()`)
- Word `delete_image` only handles inline shapes (python-docx limitation)

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
