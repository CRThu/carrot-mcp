# carrot-mcp-sys

Carrot MCP System Server — screenshot capture for multimodal analysis.

## Features

- **Multi-monitor support**: Capture individual monitors or all at once
- **Region capture**: Crop to any rectangular area using absolute screen coordinates
- **Save to file**: Optionally save captured images to disk
- **MCP-compatible output**: Returns base64-encoded PNG images ready for LLM processing

## Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info |
| `list_monitors` | List all monitors with coordinates and resolution |
| `screenshot` | Capture screenshot — supports monitor index, region coordinates, or all monitors |

## Installation

```bash
# From project root
uv sync --all-packages

# Or install standalone
pip install carrot-mcp-sys
```

## Usage

### Run as MCP server

```bash
carrot-mcp sys
python -m carrot_mcp_sys
```

### Coordinate system

All coordinates are **absolute screen pixels** with origin (0,0) at the top-left corner of the virtual screen.

```
Monitor 1 (left):  left=0,    top=0, width=1920, height=1080
Monitor 2 (right): left=1920, top=0, width=2560, height=1440
```

Use `list_monitors` to discover each monitor's position.

### Examples

**Capture full monitor:**
```json
{"tool": "screenshot", "monitor": 1}
```

**Capture an absolute region:**
```json
{"tool": "screenshot", "left": 1920, "top": 100, "width": 800, "height": 600}
```

**Capture all monitors:**
```json
{"tool": "screenshot"}
```

**Save to file:**
```json
{"tool": "screenshot", "monitor": 1, "save_path": "/tmp/capture.png"}
```

## Output format

Each monitor capture returns:
```json
{
  "width": 1920,
  "height": 1080,
  "origin": {"left": 0, "top": 0},
  "bytes": 524288,
  "image": {
    "type": "image",
    "base64": "data:image/png;base64,...",
    "mime": "image/png"
  },
  "monitor": {"index": 1, "left": 0, "top": 0, "width": 1920, "height": 1080}
}
```

## Dependencies

- `mcp>=1.28.0`
- `mss>=9.0.0` — fast cross-platform screenshot library
