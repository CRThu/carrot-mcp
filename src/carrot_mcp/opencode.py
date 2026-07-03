"""OpenCode MCP config.

Config path: ~/.config/opencode/opencode.jsonc
Backup path: %APPDATA%/carrot-mcp/agents/opencode/
"""

import json
from pathlib import Path

from carrot_mcp.backup import backup_config

CONFIG = Path.home() / ".config" / "opencode" / "opencode.jsonc"


def is_available() -> bool:
    return CONFIG.parent.exists()


def _ensure() -> None:
    if not CONFIG.exists() and is_available():
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps({"$schema": "https://opencode.ai/config.json"}, indent=2), "utf-8")


def _load() -> dict:
    if not CONFIG.exists():
        return {}
    text = CONFIG.read_text("utf-8")
    text = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("//"))
    return json.loads(text)


def _dump(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def backup() -> str:
    return backup_config("opencode", CONFIG)


def list_carrot() -> dict:
    return {k: v for k, v in _load().get("mcp", {}).items() if k.startswith("carrot-")}


def list_carrot_local() -> dict:
    return {k: v for k, v in list_carrot().items() if v.get("type") != "remote"}


def get_env(config: dict) -> dict:
    return config.get("environment")


def add(name: str, env: dict = None, use_uvx: bool = False) -> str:
    _ensure()
    b = backup()
    c = _load()
    key = f"carrot-{name}"
    if use_uvx:
        c.setdefault("mcp", {})[key] = {
            "type": "local",
            "command": ["uvx", f"carrot-mcp-{name}@latest"],
            "enabled": True,
            "environment": env or {},
        }
    else:
        c.setdefault("mcp", {})[key] = {
            "type": "local",
            "command": ["carrot-mcp", "run", name],
            "enabled": True,
            "environment": env or {},
        }
    CONFIG.write_text(_dump(c), "utf-8")
    return b


def remove(name: str) -> str:
    b = backup()
    c = _load()
    key = f"carrot-{name}" if not name.startswith("carrot-") else name
    del c["mcp"][key]
    CONFIG.write_text(_dump(c), "utf-8")
    return b
