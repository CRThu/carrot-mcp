# carrot-mcp-office

Carrot MCP Office Server — Excel and Word automation via MCP.

## Features

- **Auto-backup**: All modifications are automatically versioned to `%APPDATA%/carrot-mcp/office/`
- **Legacy format support**: Automatically converts `.doc` → `.docx` and `.xls` → `.xlsx` via win32com (Windows)
- **Version history**: Track and restore file versions

## Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info and backup configuration |

### Excel Tools

| Tool | Description |
|------|-------------|
| `workbook_metadata` | Get workbook metadata (sheet names, properties) |
| `workbook_grep` | Search for exact substring in cell values. Case-insensitive by default, or regex. |
| `create_sheet` | Create a new sheet |
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

All Excel tools accept `.xls`/`.xlsx` files (`.xls` auto-converted on Windows).

### Word Tools

| Tool | Description |
|------|-------------|
| `inspect` | Inspect document structure (paragraphs, tables, images, styles). Only returns non-empty paragraphs. |
| `get_table` | Read table content as 2D array. |
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
| `get_outline` | Get document outline as tree + flat list. Use flat array indices (0-based position) with `get_content`. |
| `get_content` | Get paragraphs, tables, and images by `section` (flat outline indices) or `paragraph` (document paragraph indices). Set `text_only=true` for leaner output. |
| `grep` | Search for exact substring in paragraphs. Case-insensitive by default, or regex. Returns matches with index, style, and surrounding context. |

All Word tools accept `.doc`/`.docx` files (`.doc` auto-converted on Windows).

### Backup Tools

| Tool | Description |
|------|-------------|
| `backup_history` | List all backup versions of a file |
| `backup_restore` | Restore a file to a specific backup version |

## Backup System

Backups are stored in `%APPDATA%/carrot-mcp/office/` with mirrored directory structure:

```
%APPDATA%/carrot-mcp/office/
├── _last_modified.txt
├── D/
│   └── docs/
│       └── reports/
│           ├── _versions.json
│           ├── file_v001.xlsx
│           ├── file_v002.xlsx
│           └── ...
```

- **Auto-versioning**: Every modification creates a new version
- **100 version limit**: Old versions are pruned when exceeded
- **14-day expiry**: Versions older than 14 days are automatically deleted
- **Version numbers**: Each mutation returns a `version` number in the result for LLM context

### Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `CARROT_MCP_BACKUP_MAX_VERSIONS` | `100` | Max versions to keep per file |
| `CARROT_MCP_BACKUP_MAX_AGE_DAYS` | `14` | Days before auto-deletion |
| `CARROT_MCP_BACKUP_ROOT` | `%APPDATA%/carrot-mcp/office/` | Override backup root directory |

## Legacy Format Conversion

When you pass a `.doc` or `.xls` file path, the server automatically:
1. Detects the legacy format
2. If a `.docx`/`.xlsx` with the same name already exists in the same directory, reuses it directly (skips conversion)
3. Otherwise converts via win32com (preserves original file)
4. Operates on the `.docx`/`.xlsx` format

Requires `pywin32` on Windows. Returns error on other platforms.

## Usage

```bash
# Standalone
uv run carrot-mcp office

# Via main CLI
uv run carrot-mcp office
```
