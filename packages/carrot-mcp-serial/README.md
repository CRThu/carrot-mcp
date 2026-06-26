# carrot-mcp-serial

Carrot MCP Serial Server - pyserial wrapper for serial port communication.

## Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info |
| `list_ports` | List available serial ports |
| `open` | Open a serial port connection (baudrate, parity, timeouts, buffer_size) |
| `close` | Close a serial port connection |
| `read` | Blocking read with timeout |
| `recv` | Non-blocking read from buffer |
| `write` | Write data (hex or ascii with escape support) |
| `script` | Execute a sequence of serial operations (write/read/wait/flush) |

## Examples

```bash
# List ports
uvx carrot-mcp-serial@latest

# MCP config
{
  "carrot-serial": {
    "command": "uvx",
    "args": ["carrot-mcp-serial@latest"]
  }
}
```

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
