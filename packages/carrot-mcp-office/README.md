# carrot-mcp-office

Carrot MCP Office Server — Excel and Word automation via MCP.

## Tools

### Excel Tools

| Tool | Description |
|------|-------------|
| `workbook_metadata` | Get workbook metadata (sheet names, properties) |
| `workbook_search` | Search for values in a sheet |
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

### Word Tools

| Tool | Description |
|------|-------------|
| `inspect` | Inspect document structure |
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

## Usage

```bash
# Standalone
uv run carrot-mcp office

# Via main CLI
uv run carrot-mcp office
```
