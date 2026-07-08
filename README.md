# Carrot MCP

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

A collection of MCP (Model Context Protocol) servers for various hardware and data interfaces.

## Installation

### uvx (no install, always latest)

Run directly without installing. Always fetches latest version.

```bash
# Run any server directly
uvx carrot-mcp-pdf@latest
uvx carrot-mcp-io@latest
uvx carrot-mcp-nfc@latest
uvx carrot-mcp-office@latest
uvx carrot-mcp-sys@latest

# Run via meta package
uvx carrot-mcp run pdf
```

### uv tool (recommended)

Persistent install with automatic PATH setup. Upgrades cleanly.

```bash
# Install all
uv tool install carrot-mcp

# Install specific servers
uv tool install carrot-mcp[pdf]
uv tool install carrot-mcp[io]
uv tool install carrot-mcp[nfc]
uv tool install carrot-mcp[office]
uv tool install carrot-mcp[sys]

# Or install sub-packages directly
uv tool install carrot-mcp-pdf
uv tool install carrot-mcp-io
uv tool install carrot-mcp-nfc
uv tool install carrot-mcp-office
uv tool install carrot-mcp-sys

# Upgrade
uv tool upgrade carrot-mcp

# Uninstall
uv tool uninstall carrot-mcp
```

### pip

Classic Python install. Requires manual PATH setup.

```bash
# Install all
pip install carrot-mcp

# Install specific servers
pip install carrot-mcp[pdf]
pip install carrot-mcp[io]
pip install carrot-mcp[nfc]
pip install carrot-mcp[office]
pip install carrot-mcp[sys]

# Or install sub-packages directly
pip install carrot-mcp-pdf
pip install carrot-mcp-io
pip install carrot-mcp-nfc
pip install carrot-mcp-office
pip install carrot-mcp-sys

# Upgrade
pip install --upgrade carrot-mcp

# Uninstall
pip uninstall carrot-mcp
```

## Quick Start

### uvx (no install, always latest)

```bash
# Run a specific server directly
uvx carrot-mcp-pdf@latest
uvx carrot-mcp-io@latest
uvx carrot-mcp-nfc@latest
uvx carrot-mcp-office@latest
uvx carrot-mcp-sys@latest

# List available servers
uvx carrot-mcp list

# Add all carrot servers to supported agents
uvx carrot-mcp mcp add

# Force uvx mode for agent configs
uvx carrot-mcp mcp add --uvx

# Force local mode
uvx carrot-mcp mcp add --local

# Remove all carrot servers from agents
uvx carrot-mcp mcp remove
```

### CLI (after uv tool or pip install)

```bash
# List all available servers
carrot-mcp list

# Run a specific server
carrot-mcp run pdf
carrot-mcp run io
carrot-mcp run nfc
carrot-mcp run office
carrot-mcp run sys

# Add all carrot servers to supported agents
carrot-mcp mcp add

# Add to specific agent(s)
carrot-mcp mcp add claude
carrot-mcp mcp add claude mimocode

# Force uvx mode (auto-update)
carrot-mcp mcp add --uvx

# Force local mode
carrot-mcp mcp add --local

# Remove all carrot servers from agents
carrot-mcp mcp remove

# Remove from specific agent(s)
carrot-mcp mcp remove claude

# Run with uv
uv run carrot-mcp run office
```

### Python module

```bash
python -m carrot_mcp_pdf
python -m carrot_mcp_io
python -m carrot_mcp_nfc
python -m carrot_mcp_office
python -m carrot_mcp_sys
```

## Available Servers

| Server | Package | Category | Description |
|--------|---------|----------|-------------|
| PDF | `carrot-mcp-pdf` | Document | PDF processing |
| Office | `carrot-mcp-office` | Document | Excel & Word automation with auto-backup |
| IO | `carrot-mcp-io` | Hardware | Serial, TCP, UDP communication |
| NFC | `carrot-mcp-nfc` | Hardware | NFC reader (PN532, CLRC663) |
| SYS | `carrot-mcp-sys` | System | Screenshot capture for multimodal analysis |

## Document Servers

### PDF MCP Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info |
| `get_toc` | Get table of contents with page ranges |
| `get_pages` | Convert specific pages to markdown (supports multimodal/OCR/force_ocr) |
| `grep` | Search for exact substring in PDF pages (case-insensitive, supports regex) |

**Environment variables:**

| Variable | Description |
|----------|-------------|
| `CARROT_MCP_MODEL` | Vision model name (required if using OCR) |
| `CARROT_MCP_APIKEY` | API key for the vision model |
| `CARROT_MCP_PROXY` | HTTP proxy URL for API calls |
| `CARROT_MCP_FORCE_MULTIMODAL` | `true` = always return images; `false` = always run OCR |

### Office MCP Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info and backup configuration |

#### Excel Tools

| Tool | Description |
|------|-------------|
| `workbook_metadata` | Get workbook metadata (sheet names, properties) |
| `workbook_grep` | Search for exact substring in cell values (case-insensitive, supports regex) |
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

#### Word Tools

| Tool | Description |
|------|-------------|
| `inspect` | Inspect document structure (paragraphs, tables, images) |
| `get_outline` | Get document outline as tree + flat list |
| `get_content` | Get paragraphs, tables, and images by section or paragraph indices |
| `get_table` | Read table content as 2D array |
| `grep` | Search for exact substring in paragraphs (case-insensitive, supports regex) |
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

#### Backup Tools

| Tool | Description |
|------|-------------|
| `backup_history` | List all backup versions of a file |
| `backup_restore` | Restore a file to a specific backup version |

Features:
- **Auto-backup**: All modifications are automatically versioned
- **Legacy format support**: `.doc` → `.docx`, `.xls` → `.xlsx` via win32com (Windows)
- **100 version limit** with 14-day expiry per file

**Environment variables:**

| Variable | Description |
|----------|-------------|
| `CARROT_MCP_BACKUP_MAX_VERSIONS` | Max backup versions per file (default: 100) |
| `CARROT_MCP_BACKUP_MAX_AGE_DAYS` | Days before backup expiry (default: 14) |
| `CARROT_MCP_BACKUP_ROOT` | Custom backup directory |

## Hardware Servers

### IO MCP Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info |
| `list_transports` | List available transport types and serial ports |
| `open` | Open a connection (serial, tcp, udp) |
| `close` | Close a connection |
| `read` | Blocking read from buffer with timeout |
| `recv` | Non-blocking read from buffer |
| `write` | Write data (hex or ascii with escape support) |
| `script` | Execute a sequence of I/O operations (write/read/wait/flush) |
| `history` | Get operation history for a connection |

### NFC MCP Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info |
| `list_readers` | List available reader types and transports |
| `connect` | Connect to NFC reader |
| `disconnect` | Disconnect from reader |
| `find` | Find and activate an NFC card |
| `transceive` | Raw frame exchange with bit-level control |
| `reqa` | ISO14443-A REQA |
| `wupa` | ISO14443-A WUPA |
| `halt` | ISO14443-A HALT |
| `select` | ISO14443-A SELECT |
| `anticoll` | ISO14443-A anti-collision |
| `field_on` | Turn on RF field |
| `field_off` | Turn off RF field |
| `script` | Execute a sequence of NFC operations |
| `trace_get` | Get trace log entries |
| `trace_clear` | Clear trace log buffer |

### System MCP Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info |
| `list_monitors` | List all monitors with coordinates and resolution |
| `screenshot` | Capture screenshot(s) - supports monitor index, region coordinates, or all monitors |

## MCP Configuration

### Auto-config (recommended)

```bash
carrot-mcp mcp add
```

This adds all servers to supported agents (claude, opencode, mimocode). Auto-detects whether to use `carrot-mcp run` or `uvx` based on what's installed. Use `--uvx` or `--local` to override.

### Manual config

**Claude Desktop** (`~/.claude.json`):

```json
{
  "mcpServers": {
    "carrot-pdf": {
      "command": "carrot-mcp",
      "args": ["run", "pdf"]
    },
    "carrot-office": {
      "command": "carrot-mcp",
      "args": ["run", "office"]
    },
    "carrot-io": {
      "command": "carrot-mcp",
      "args": ["run", "io"]
    },
    "carrot-nfc": {
      "command": "carrot-mcp",
      "args": ["run", "nfc"]
    },
    "carrot-sys": {
      "command": "carrot-mcp",
      "args": ["run", "sys"]
    }
  }
}
```

**OpenCode / MiMoCode** (`~/.config/opencode/opencode.jsonc` or `~/.config/mimocode/mimocode.jsonc`):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "carrot-pdf": {
      "type": "local",
      "command": ["carrot-mcp", "run", "pdf"],
      "enabled": true,
      "environment": {}
    },
    "carrot-office": {
      "type": "local",
      "command": ["carrot-mcp", "run", "office"],
      "enabled": true,
      "environment": {}
    },
    "carrot-io": {
      "type": "local",
      "command": ["carrot-mcp", "run", "io"],
      "enabled": true,
      "environment": {}
    },
    "carrot-nfc": {
      "type": "local",
      "command": ["carrot-mcp", "run", "nfc"],
      "enabled": true,
      "environment": {}
    },
    "carrot-sys": {
      "type": "local",
      "command": ["carrot-mcp", "run", "sys"],
      "enabled": true,
      "environment": {}
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

# Run tests for specific server
uv run pytest tests/pdf/ -v
uv run pytest tests/office/ -v
uv run pytest tests/io/ -v
uv run pytest tests/nfc/ -v
uv run pytest tests/sys/ -v

# Bump version and release
bump.bat                        # interactive
bump.bat carrot-mcp-office      # direct package
```

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.
