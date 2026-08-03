"""Gemini / Antigravity MCP config.

Config path: ~/.gemini/config/mcp_config.json
Backup path: %APPDATA%/carrot-mcp/agents/gemini/
"""

import json
from pathlib import Path

from carrot_mcp.backup import backup_config

CONFIG = Path.home() / ".gemini" / "config" / "mcp_config.json"


def is_available() -> bool:
    return CONFIG.parent.parent.exists() or CONFIG.exists()


def _ensure() -> None:
    if not CONFIG.exists() and is_available():
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text("{}", "utf-8")


def _load() -> dict:
    if not CONFIG.exists():
        return {}
    text = CONFIG.read_text("utf-8").strip()
    if not text:
        return {}
    text = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("//"))
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return {}


def _dump(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def backup() -> str:
    return backup_config("gemini", CONFIG)


def list_carrot() -> dict:
    return {k: v for k, v in _load().get("mcpServers", {}).items() if k.startswith("carrot-")}


def list_carrot_local() -> dict:
    return {k: v for k, v in list_carrot().items() if v.get("type") != "http"}


def get_env(config: dict) -> dict:
    return config.get("env")


def add(name: str, env: dict = None, use_uvx: bool = False) -> str:
    _ensure()
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
    if "mcpServers" in c and key in c["mcpServers"]:
        del c["mcpServers"][key]
    CONFIG.write_text(_dump(c), "utf-8")
    return b
