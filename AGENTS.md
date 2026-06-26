# AGENTS.md

## Project Overview

Carrot MCP is a collection of MCP (Model Context Protocol) servers for hardware and data interfaces.

## Project Structure

```
carrot-mcp/
├── pyproject.toml              # Root: meta package, workspace config
├── src/carrot_mcp/             # Main package (CLI entry point)
│   ├── __init__.py
│   └── cli.py                  # carrot-mcp command
├── packages/
│   ├── carrot-mcp-ds/          # Datasheet MCP server
│   │   ├── pyproject.toml
│   │   └── src/carrot_mcp_ds/
│   ├── carrot-mcp-serial/      # Serial port MCP server
│   │   ├── pyproject.toml
│   │   └── src/carrot_mcp_serial/
│   └── carrot-mcp-nfc/         # NFC reader MCP server
│       ├── pyproject.toml
│       └── src/carrot_mcp_nfc/
└── tests/
    ├── ds/
    ├── serial/
    └── nfc/
```

## Build & Test Commands

```bash
# Install dependencies
uv sync --all-packages

# Run tests
uv run pytest

# Run servers
uv run carrot-mcp ds
uv run carrot-mcp serial
uv run carrot-mcp nfc
uv run python -m carrot_mcp_ds
```

## Code Style

- Python 3.10+
- Use type hints
- Follow existing patterns in the codebase
- Each MCP server follows the same structure: server.py with FastMCP

## Adding a New MCP Server

1. Create directory: `packages/carrot-mcp-<name>/`
2. Add `pyproject.toml` with mcp dependency, scripts entry, and entry point:
   ```toml
   [project.scripts]
   carrot-mcp-<name> = "carrot_mcp_<name>.server:main"

   [project.entry-points."carrot_mcp.servers"]
   <name> = "carrot_mcp_<name>.server:mcp"
   ```
3. Create `src/carrot_mcp_<name>/server.py` with FastMCP
4. Add to root `pyproject.toml` dependencies and uv.sources
5. Write tests in `tests/<name>/`

CLI auto-discovers servers via entry points - no need to update cli.py.

## License

Apache 2.0
