# carrot-mcp-pdf

Carrot MCP PDF Server — convert PDFs to structured markdown with optional OCR.

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
| `get_pages` | Convert specific pages to markdown (supports multimodal/OCR/force_ocr) |
| `create_task` | Start background full PDF conversion (multimodal/force_ocr option) |
| `get_status` | Check progress of background conversion task |

## Architecture

```
Application Layer (server.py — MCP tools, thin routing)
    ↓ get_toc/get_pages/create_task
Conversion Layer (converter.py — pymupdf4llm → markdown + images)
    ↓ force_ocr=True
OCR Layer (ocr.py — litellm vision API)
    ↓ multimodal=False
Cache Layer (cache.py — JSON: %APPDATA%/carrot-mcp/pdf/<md5>.json)
```

- **server.py** — MCP tool definitions only, delegates to converter/cache
- **converter.py** — PDF conversion, image processing, content parsing, VLM config
- **ocr.py** — Vision model OCR via litellm (single responsibility)
- **cache.py** — Cache/task persistence, path management, parse_page_range

- **Cache**: `%APPDATA%/carrot-mcp/pdf/<md5>.json`
- **Dual format**: each page caches both `content` (base64) and `ocr_content` (OCR text)
- **Force OCR**: PDF-level flag — renders page as image and OCRs it; for scanned PDFs or garbled text
- **Background tasks**: separate `<hash>_tasks.json` with progress tracking

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CARROT_MCP_MODEL` | — | Vision model name for OCR (must be configured if using OCR) |
| `CARROT_MCP_APIKEY` | — | API key for the vision model (must be configured if using OCR) |
| `CARROT_MCP_PROXY` | — | HTTP proxy URL for API calls |
| `CARROT_MCP_FORCE_MULTIMODAL` | — | `true` = always return images as base64; `false` = always run OCR. When not set, uses tool parameter. If VLM not configured (no model/apikey), falls back to base64 with warning. |

## Development

```bash
# Run tests
uv run pytest tests/pdf/ -v
```
