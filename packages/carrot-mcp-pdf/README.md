# carrot-mcp-pdf

Carrot MCP PDF Server — convert PDFs to structured markdown or rendered page images.

## Installation

```bash
uv sync --all-packages
```

## Usage

```bash
# Run as MCP server
uv run carrot-mcp-pdf

# Or via main CLI
uv run carrot-mcp pdf

# Or as Python module
uv run python -m carrot_mcp_pdf
```

## Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info |
| `get_toc` | Get table of contents with page ranges |
| `get_pages` | Convert specific pages to markdown or rendered images. Accepts `pages` as int (single page), str (range like '1-5,8,10-12'), list, or None. Returns `list[TextContent \| ImageContent]` |
| `grep` | Search for exact substring in PDF pages. Case-insensitive by default, or regex. Returns matches with page number, text, and surrounding context. |

## Architecture

```
Application Layer (server.py — MCP tools, thin routing)
    ↓ get_toc/get_pages
Conversion Layer (converter.py — pymupdf4llm → markdown + images)
    ↓ extract_text=False → render_page_as_image
Cache Layer (cache.py — JSON: %APPDATA%/carrot-mcp/pdf/<md5>.json)
```

- **server.py** — MCP tool definitions only, delegates to converter/cache
- **converter.py** — PDF conversion, image processing, content parsing
- **cache.py** — Cache persistence, path management, parse_page_range

- **Cache**: `%APPDATA%/carrot-mcp/pdf/<md5>.json`
- **Content blocks**: each page caches ordered blocks `[{type: "text", data: ...}, {type: "image", data: base64_str, mime: ...}]`
- **Image return**: images returned as MCP `ImageContent` attachments (no base64 truncation)

## Development

```bash
# Run tests
uv run pytest tests/pdf/ -v
```
