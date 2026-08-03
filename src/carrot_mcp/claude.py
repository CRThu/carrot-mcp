"""Claude Code MCP config.

Config path: ~/.claude.json
Backup path: %APPDATA%/carrot-mcp/agents/claude/
"""

import json
from pathlib import Path

from carrot_mcp.backup import backup_config

CONFIG = Path.home() / ".claude.json"


def is_available() -> bool:
    return CONFIG.exists()


def _load() -> dict:
    if not CONFIG.exists():
        return {}
    text = CONFIG.read_text("utf-8").strip()
    if not text:
        return {}
    text = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("//"))
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, ValueError):
        return {}


def _dump(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def backup() -> str:
    return backup_config("claude", CONFIG)


def list_carrot() -> dict:
    return {k: v for k, v in _load().get("mcpServers", {}).items() if k.startswith("carrot-")}


def list_carrot_local() -> dict:
    return {k: v for k, v in list_carrot().items() if v.get("type") != "http"}


def get_env(config: dict) -> dict:
    return config.get("env")


def add(name: str, env: dict = None, use_uvx: bool = False) -> str:
    b = backup()
    c = _load()
    key = f"carrot-{name}"
    if use_uvx:
        c.setdefault("mcpServers", {})[key] = {
            "command": "uvx",
            "args": [f"carrot-mcp-{name}@latest"],
            "env": env or {},
        }
    else:
        c.setdefault("mcpServers", {})[key] = {
            "command": "carrot-mcp",
            "args": ["run", name],
            "env": env or {},
        }
    CONFIG.write_text(_dump(c), "utf-8")
    return b


def remove(name: str) -> str:
    b = backup()
    c = _load()
    key = f"carrot-{name}" if not name.startswith("carrot-") else name
    del c["mcpServers"][key]
    CONFIG.write_text(_dump(c), "utf-8")
    return b
