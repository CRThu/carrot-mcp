# carrot-mcp-serial

Carrot MCP Serial Server - pyserial wrapper for serial port communication.

## Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info |
| `list` | List available serial ports |
| `open` | Open a serial port connection |
| `close` | Close a serial port connection |
| `read` | Blocking read with timeout |
| `recv` | Non-blocking read from buffer |
| `write` | Write data (hex or ascii with escape support) |

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

- `read`/`recv` with `fmt="hex"` returns `data_hex` (uppercase, e.g. `"48656C6C6F"`)
- `read`/`recv` with `fmt="ascii"` returns `data_ascii` with escape handling (e.g. `"Hello\nWorld"`)
- `write` supports `hex` or `ascii` input, ascii supports escape sequences (`\n`, `\x00`)
