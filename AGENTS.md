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
│   ├── carrot-mcp-io/          # IO MCP server (serial, TCP, UDP)
│   │   ├── pyproject.toml
│   │   └── src/carrot_mcp_io/
│   └── carrot-mcp-nfc/         # NFC reader MCP server
│       ├── pyproject.toml
│       └── src/carrot_mcp_nfc/
│   └── carrot-mcp-sys/         # System MCP server (screenshot, keyboard, app launcher)
│       ├── pyproject.toml
│       └── src/carrot_mcp_sys/
└── tests/
    ├── pdf/
    ├── office/
    ├── io/
    │   ├── test_transport.py
    │   ├── test_channel.py
    │   ├── test_logger.py
    │   └── test_server.py
    ├── nfc/
    └── sys/
```

## Build & Test Commands

```bash
# Install dependencies
uv sync --all-packages

# Run tests
uv run pytest

# Run tests for specific server
uv run pytest tests/io/ -v

# Run single test module
uv run pytest tests/io/test_channel.py -v

# Run servers
uv run carrot-mcp pdf
uv run carrot-mcp office
uv run carrot-mcp serial
uv run carrot-mcp nfc
uv run carrot-mcp sys
uv run python -m carrot_mcp_pdf
uv run python -m carrot_mcp_office
uv run python -m carrot_mcp_sys
```

## Code Style

- Python 3.10+
- Use type hints
- Follow existing patterns in the codebase
- Each MCP server follows the same structure: server.py with FastMCP
- Tools return dict with `{"status": "ok"|"error", ...}` format, except tools that return images (use `list[TextContent | ImageContent]`)
- Each server implements a `version` tool using `importlib.metadata.version`
- Version is read from `pyproject.toml` — do NOT hardcode `__version__` in `__init__.py`
- **Test directories must NOT have `__init__.py`** — it shadows the `serial` package from pyserial
- 修改代码（函数名、工具名等）后，必须同步更新 `AGENTS.md` 和各包的 `README.md`，并运行 `uv run pytest` 验证

## IO MCP Server Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info |
| `list_transports` | List available transport types and serial ports |
| `open` | Open a connection (serial, tcp, udp) |
| `close` | Close a connection |
| `read` | Blocking read from buffer with timeout |
| `recv` | Non-blocking read from buffer (returns available data) |
| `write` | Write data (hex or ascii with escape support) |
| `script` | Execute a sequence of I/O operations (write/read/wait/flush) |
| `history` | Get operation history for a connection |

### Architecture

```
Application Layer (MCP tools)
    ↓ read/write (all via Channel buffers)
Channel Layer (Channel: RX/TX buffers with backpressure, Event-driven wait, observer events)
    ↓ polling via daemon thread (only thread touching hardware)
Transport Layer (Transport ABC → SerialTransport / TcpTransport / UdpTransport)
    ↓ raw I/O
Hardware Layer (serial.Serial / socket)
```

**Separation of concerns (low coupling, high cohesion):**

- `transport.py`: `Transport` ABC + `SerialTransport` + `TcpTransport` + `UdpTransport` — pure FIFO interface (read/write/buffer-status/close), context manager support, no wait/blocking semantics
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

## PDF MCP Server Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info |
| `get_toc` | Get table of contents with page ranges |
| `get_pages` | Convert specific pages to markdown (returns `list[TextContent \| ImageContent]`) |
| `create_task` | Start background full PDF conversion (multimodal/force_ocr option) |
| `get_status` | Check progress of background conversion task |

### Architecture

```
Application Layer (server.py — MCP tools, thin routing)
    ↓ get_toc/get_pages/create_task
Conversion Layer (converter.py — pymupdf4llm → markdown + images)
    ↓ force_ocr=True
OCR Layer (ocr.py — litellm vision API)
    ↓ multimodal=False
Cache Layer (cache.py — JSON: %APPDATA%/carrot-mcp/pdf/<hash>.json)
```

- **server.py** — MCP tool definitions only, delegates to converter/cache
- **converter.py** — PDF conversion, image processing, content parsing, VLM config
- **ocr.py** — Vision model OCR via litellm (single responsibility)
- **cache.py** — Cache/task persistence, path management, parse_page_range

- Cache: `%APPDATA%/carrot-mcp/pdf/<md5(pdf_path)>.json`
- JSON structure: `{name, size, path, total_pages, force_ocr, toc, pages: {page_num: {content: [...], ocr_content: [...]}}}`
- Content stored as ordered blocks: `[{type: "text", data: "..."}, {"type": "image", data: bytes, mime: "..."}]`
- Each page caches **both** formats: `content` (raw image bytes) and `ocr_content` (OCR text)
- `get_pages` returns `list[TextContent | ImageContent]` — metadata in first TextContent, images as ImageContent attachments (no base64 truncation)
- `multimodal=True` returns `content` with images as `ImageContent`, `multimodal=False` returns `ocr_content` as text
- `force_ocr` is PDF-level flag (not per-page) — if a few pages are wrong, the whole PDF is likely wrong
- When `force_ocr=True`: renders entire page as PNG image, calls OCR API, caches result; future requests also use OCR
- Background conversion via `threading.Thread` with progress tracking in separate `<hash>_tasks.json`
- Completed tasks auto-delete from tasks.json; failed tasks retained for debugging
- On restart, `create_task` resumes by skipping already-cached pages

**Environment variables:**
- `CARROT_MCP_MODEL`: Vision model name (must be configured if using OCR)
- `CARROT_MCP_APIKEY`: API key for the vision model (must be configured if using OCR)
- `CARROT_MCP_PROXY`: HTTP proxy URL for API calls
- `CARROT_MCP_FORCE_MULTIMODAL`: `true` = always return images as attachments; `false` = always run OCR. When not set, uses tool parameter. If VLM not configured (no model/apikey), falls back to attachments with warning.

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

## Sys MCP Server Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info |
| `list_monitors` | List all available monitors with coordinates and resolution |
| `screenshot` | Capture screenshot(s). Args: `monitor` (1-based index, optional), `left`/`top`/`width`/`height` (region coords), `save_path` (file output). Returns `list[TextContent \| ImageContent]` — JSON metadata + PNG images as attachments |

### Architecture

```
Application Layer (MCP tools)
    ↓ screenshot via mss library
Library Layer (mss - native OS screenshot API)
    ↓ raw pixel capture
Hardware Layer (display output)
```

- All coordinates are **absolute screen pixels** (origin at top-left of virtual screen)
- `list_monitors` skips index 0 (virtual combined screen), returns 1-based indices
- `screenshot(monitor=N)` captures full monitor; region coordinates are absolute (no offset needed)
- Single-monitor systems auto-select monitor when no args provided
- Returns `list[TextContent | ImageContent]` — metadata in TextContent (JSON), images as separate ImageContent attachments via MCP content channel (avoids base64-in-JSON truncation)
- Each monitor returned as separate ImageContent entry
- Optional `save_path` for saving to file

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

## Agent Config Modules

CLI manages MCP server configs for different agents via entry points.

**Supported agents:**

| Agent | Config Path | Backup Path | Env Key |
|-------|-------------|-------------|---------|
| claude | `~/.claude.json` | `~/.claude/` | `env` |
| mimocode | `~/.config/mimocode/mimocode.jsonc` | `~/.config/mimocode/` | `environment` |
| opencode | `~/.config/opencode/opencode.jsonc` | `~/.config/opencode/` | `environment` |

**CLI commands:**
```bash
carrot-mcp run <server>    # Run MCP server
carrot-mcp list             # List available servers
carrot-mcp add              # Add all carrot servers to all agents
carrot-mcp remove           # Remove all carrot servers from all agents
```

**Agent detection:**
- claude: checks if `~/.claude.json` exists
- mimocode/opencode: checks if parent directory exists (creates config with `$schema` if missing)

**Env preservation:**
- When adding servers, existing `env`/`environment` configs are preserved
- Servers not in the new list are removed

**Adding a new agent:**
1. Create `src/carrot_mcp/<agent>.py` with functions: `is_available`, `add`, `remove`, `list_carrot`, `get_env`
2. Add entry point in `pyproject.toml`:
   ```toml
   [project.entry-points."carrot_mcp.agents"]
   <agent> = "carrot_mcp.<agent>"
   ```
3. Write tests in `tests/test_agents.py`

## License

Apache 2.0
