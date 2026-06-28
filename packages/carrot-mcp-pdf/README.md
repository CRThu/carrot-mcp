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
| `get_pages` | Convert specific pages to markdown (supports multimodal/OCR) |
| `create_task` | Start background full PDF conversion (multimodal option) |
| `get_status` | Check progress of background conversion task |

## Architecture

```
Application Layer (MCP tools: get_toc, get_pages, create_task, get_status)
    ↓ pymupdf4llm
Conversion Layer (markdown + images)
    ↓
Cache Layer (JSON: %APPDATA%/carrot-mcp/pdf/<md5>.json)
    ↓ multimodal=False
OCR Layer (litellm vision API)
```

- **Cache**: `%APPDATA%/carrot-mcp/pdf/<md5(pdf_path)>.json`
- **Content blocks**: ordered `[{type: "text", data: "..."}, {type: "image", base64: "...", mime: "..."}]`
- **Background tasks**: separate `<hash>_tasks.json` with progress tracking

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CARROT_MCP_MODEL` | — | Vision model name for OCR (must be configured if using OCR) |
| `CARROT_MCP_APIKEY` | — | API key for the vision model (must be configured if using OCR) |
| `CARROT_MCP_PROXY` | — | HTTP proxy URL for API calls |
| `CARROT_MCP_FORCE_MULTIMODAL` | — | `true` = always return images as base64; `false` = always run OCR. When not set, uses tool parameter. |

## Development

```bash
# Run tests
uv run pytest tests/pdf/ -v
```
