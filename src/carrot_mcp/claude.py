"""Claude Code MCP config.

Config path: ~/.claude.json
Backup path: ~/.claude/
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

CONFIG = Path.home() / ".claude.json"
BACKUP_DIR = Path.home() / ".claude"


def is_available() -> bool:
    return CONFIG.exists()


def _load() -> dict:
    if not CONFIG.exists():
        return {}
    return json.loads(CONFIG.read_text("utf-8"))


def _dump(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def backup() -> str:
    if not CONFIG.exists():
        return ""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    b = BACKUP_DIR / f".claude.json.backup.{ts}"
    shutil.copy2(CONFIG, b)
    return str(b)


def list_carrot() -> dict:
    return {k: v for k, v in _load().get("mcpServers", {}).items() if k.startswith("carrot-")}


def get_env(config: dict) -> dict:
    return config.get("env")


def add(name: str, env: dict = None) -> str:
    b = backup()
    c = _load()
    key = f"carrot-{name}"
    c.setdefault("mcpServers", {})[key] = {
        "command": "uvx",
        "args": [f"carrot-mcp-{name}@latest"],
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
