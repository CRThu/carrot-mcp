# carrot-mcp-io

Carrot MCP IO Server - serial, TCP, UDP transport wrapper for hardware and network communication.

## Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info |
| `list_transports` | List available transport types and serial ports |
| `open` | Open a connection (serial, tcp, udp) |
| `close` | Close a connection |
| `read` | Blocking read with timeout |
| `recv` | Non-blocking read from buffer |
| `write` | Buffered write (hex or ascii with escape support) |
| `script` | Execute a sequence of I/O operations (write/read/wait/flush) |
| `history` | Get operation history for a connection |

## Transports

### Serial
```json
{
  "open": {
    "port": "COM3",
    "transport": "serial",
    "baudrate": 115200
  }
}
```

### TCP
```json
{
  "open": {
    "port": "mydevice",
    "transport": "tcp",
    "host": "192.168.1.100",
    "net_port": 5000
  }
}
```

### UDP
```json
{
  "open": {
    "port": "sensor",
    "transport": "udp",
    "host": "192.168.1.200",
    "net_port": 8888
  }
}
```

## Examples

```bash
# List available transports
uvx carrot-mcp-io@latest

# MCP config
{
  "carrot-io": {
    "command": "uvx",
    "args": ["carrot-mcp-io@latest"]
  }
}
```

## Buffer Behavior (Backpressure)

- **RX buffer**: when full, the poll thread stops reading from hardware/network. Data stays in the OS buffer until the consumer frees space. No data is silently dropped.
- **TX buffer**: when full, `write()` blocks until the poll thread drains enough space. If `write_timeout` expires, a `TimeoutError` is raised.
- Buffer size is configurable via the `buffer_size` parameter on `open` (default 1MB).

## Return Format

All tools return dict with `{"status": "ok"|"error", ...}`.

- `read`/`recv` returns `data` in the specified format (default "hex", uppercase e.g. `"48656C6C6F"`)
- `read`/`recv` with `fmt="ascii"` returns escaped string (e.g. `"Hello\nWorld"`)
- `write` supports `hex` or `ascii` input, ascii supports escape sequences (`\n`, `\x00`)
- `script` executes a sequence of operations, each step returns its result

### Script Example

All read params are optional with defaults: `size=256`, `timeout=1.0`, `expect=None`, `on_mismatch="stop"`.

```json
[
  {"op": "write", "data": "AA"},
  {"op": "wait", "ms": 10},
  {"op": "write", "data": "BB"},
  {"op": "read", "size": 1, "timeout": 1.0, "expect": "CC"}
]
```

Minimal read (use defaults):

```json
[
  {"op": "write", "data": "AA"},
  {"op": "read"}
]
```

Use `fmt="ascii"` for ASCII mode:

```json
[
  {"op": "write", "data": "Hello"},
  {"op": "read", "size": 10}
]
```

Note: `expect` with default `on_mismatch="stop"` will stop script on mismatch. Use `on_mismatch="continue"` to only check without stopping.

### Script Return Format

Each step result contains:
- `op`: Operation type ("write"|"read"|"wait"|"flush")
- `step`: Step index (0-based)
- `status`: "ok" or "error"

Additional fields by op:
- write: `{bytes_written}`
- read: `{data, length}` + `{matched, expected}` if expect provided
- wait: `{ms}`
- On error: `{message}`

Example:
```json
[
  {"op": "write", "step": 0, "status": "ok", "bytes_written": 2},
  {"op": "read", "step": 1, "status": "ok", "data": "AABB", "length": 2, "matched": true}
]
```
