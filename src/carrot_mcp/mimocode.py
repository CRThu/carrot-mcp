"""MiMoCode MCP config.

Config path: ~/.config/mimocode/mimocode.jsonc
Backup path: ~/.config/mimocode/
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

CONFIG = Path.home() / ".config" / "mimocode" / "mimocode.jsonc"


def is_available() -> bool:
    return CONFIG.parent.exists()


def _ensure() -> None:
    if not CONFIG.exists() and is_available():
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text("{}", "utf-8")


def _load() -> dict:
    if not CONFIG.exists():
        return {}
    text = CONFIG.read_text("utf-8")
    text = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("//"))
    return json.loads(text)


def _dump(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def backup() -> str:
    if not CONFIG.exists():
        return ""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    b = CONFIG.parent / f"mimocode.jsonc.backup.{ts}"
    shutil.copy2(CONFIG, b)
    return str(b)


def list_carrot() -> dict:
    return {k: v for k, v in _load().get("mcp", {}).items() if k.startswith("carrot-")}


def get_env(config: dict) -> dict:
    return config.get("environment")


def add(name: str, env: dict = None) -> str:
    _ensure()
    b = backup()
    c = _load()
    key = f"carrot-{name}"
    c.setdefault("mcp", {})[key] = {
        "type": "local",
        "command": ["uvx", f"carrot-mcp-{name}@latest"],
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
