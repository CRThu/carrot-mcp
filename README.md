# Carrot MCP

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

A collection of MCP (Model Context Protocol) servers for various hardware and data interfaces.

## Installation

### pip

```bash
pip install carrot-mcp
```

This installs all MCP servers (pdf, io, nfc, office) by default.

### uv

```bash
uv pip install carrot-mcp
```

### Install specific servers only

```bash
# pip or uv
pip install carrot-mcp[pdf]
pip install carrot-mcp[io]
pip install carrot-mcp[nfc]
pip install carrot-mcp[office]
```

### Or install sub-packages directly

```bash
pip install carrot-mcp-pdf
pip install carrot-mcp-io
pip install carrot-mcp-nfc
pip install carrot-mcp-office
```

## Quick Start

### uvx (recommended)

```bash
# Run a specific server directly (no install needed)
uvx carrot-mcp-pdf@latest
uvx carrot-mcp-io@latest
uvx carrot-mcp-nfc@latest
uvx carrot-mcp-office@latest
```

### CLI

```bash
# List all available servers
carrot-mcp list

# Run a specific server
carrot-mcp pdf
carrot-mcp io
carrot-mcp nfc
carrot-mcp office

# Run with uv
uv run carrot-mcp office
```

### Python module

```bash
python -m carrot_mcp_pdf
python -m carrot_mcp_io
python -m carrot_mcp_nfc
python -m carrot_mcp_office
```

## Available Servers

| Server | Package | Category | Description |
|--------|---------|----------|-------------|
| PDF | `carrot-mcp-pdf` | Document | PDF processing |
| Office | `carrot-mcp-office` | Document | Excel & Word automation with auto-backup |
| IO | `carrot-mcp-io` | Hardware | Serial, TCP, UDP communication |
| NFC | `carrot-mcp-nfc` | Hardware | NFC reader (PN532, CLRC663) |

## Document Servers

### PDF MCP Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info |
| `get_toc` | Get table of contents with page ranges |
| `get_pages` | Convert specific pages to markdown (supports multimodal/OCR/force_ocr) |
| `create_task` | Start background full PDF conversion (multimodal/force_ocr option) |
| `get_status` | Check progress of background conversion task |

### Office MCP Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info and backup configuration |

#### Excel Tools

| Tool | Description |
|------|-------------|
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

#### Word Tools

| Tool | Description |
|------|-------------|
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

#### Backup Tools

| Tool | Description |
|------|-------------|
| `backup_history` | List all backup versions of a file |
| `backup_restore` | Restore a file to a specific backup version |

Features:
- **Auto-backup**: All modifications are automatically versioned
- **Legacy format support**: `.doc` → `.docx`, `.xls` → `.xlsx` via win32com (Windows)
- **100 version limit** with 14-day expiry per file

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
| `exchange` | Data exchange with auto CRC |
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

## MCP Configuration

Add to your MCP client config (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "carrot-pdf": {
      "command": "uvx",
      "args": ["carrot-mcp-pdf@latest"]
    },
    "carrot-office": {
      "command": "uvx",
      "args": ["carrot-mcp-office@latest"]
    },
    "carrot-io": {
      "command": "uvx",
      "args": ["carrot-mcp-io@latest"]
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

# Run tests for specific server
uv run pytest tests/pdf/ -v
uv run pytest tests/office/ -v
uv run pytest tests/io/ -v
uv run pytest tests/nfc/ -v

# Bump version and release
bump.bat                        # interactive
bump.bat carrot-mcp-office      # direct package
```

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.
