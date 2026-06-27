# Carrot MCP

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

A collection of MCP (Model Context Protocol) servers for various hardware and data interfaces.

## Installation

### pip

```bash
pip install carrot-mcp
```

This installs all MCP servers (ds, serial, nfc) by default.

### uv

```bash
uv pip install carrot-mcp
```

### Install specific servers only

```bash
# pip or uv
pip install carrot-mcp[ds]
pip install carrot-mcp[serial]
pip install carrot-mcp[nfc]
```

### Or install sub-packages directly

```bash
pip install carrot-mcp-ds
pip install carrot-mcp-serial
pip install carrot-mcp-nfc
```

## Quick Start

### uvx (recommended)

```bash
# Run a specific server directly (no install needed)
uvx carrot-mcp-ds@latest
uvx carrot-mcp-serial@latest
uvx carrot-mcp-nfc@latest
```

### CLI

```bash
# List all available servers
carrot-mcp list

# Run a specific server
carrot-mcp ds
carrot-mcp serial
carrot-mcp nfc

# Run with uv
uv run carrot-mcp ds
```

### Python module

```bash
python -m carrot_mcp_ds
python -m carrot_mcp_serial
python -m carrot_mcp_nfc
```

## Available Servers

| Server | Package | Description |
|--------|---------|-------------|
| DS | `carrot-mcp-ds` | Datasheet MCP server |
| Serial | `carrot-mcp-serial` | Serial port MCP server |
| NFC | `carrot-mcp-nfc` | NFC reader MCP server |

## Serial MCP Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info |
| `list_ports` | List available serial ports |
| `open` | Open a serial port (baudrate, parity, timeouts, buffer_size) |
| `close` | Close a serial port |
| `read` | Blocking read from buffer with timeout |
| `recv` | Non-blocking read from buffer |
| `write` | Write data (hex or ascii with escape support) |
| `script` | Execute a sequence of serial operations (write/read/wait/flush) |
| `history` | Get operation history for a port |

## MCP Configuration

Add to your MCP client config (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "carrot-ds": {
      "command": "uvx",
      "args": ["carrot-mcp-ds@latest"]
    },
    "carrot-serial": {
      "command": "uvx",
      "args": ["carrot-mcp-serial@latest"]
    },
    "carrot-nfc": {
      "command": "uvx",
      "args": ["carrot-mcp-nfc@latest"]
    }
  }
}
```

## Development

```bash
# Clone and setup
git clone <repo-url>
cd carrot-mcp
uv sync --all-packages

# Run tests
uv run pytest

# Bump version and release
bump.bat                        # interactive
bump.bat carrot-mcp-ds          # direct package
```

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.
