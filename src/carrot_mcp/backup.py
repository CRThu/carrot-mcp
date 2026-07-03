"""Unified config backup management.

All agent config backups are stored in:
    %APPDATA%/carrot-mcp/agents/<agent_name>/  (Windows)
    ~/.local/share/carrot-mcp/agents/<agent_name>/  (Linux/macOS)
"""

import os
import shutil
from datetime import datetime
from pathlib import Path


def get_backup_dir(agent_name: str) -> Path:
    """Return backup directory for the given agent, creating it if needed."""
    base = os.environ.get("APPDATA", os.path.expanduser("~/.local/share"))
    d = Path(base) / "carrot-mcp" / "agents" / agent_name
    d.mkdir(parents=True, exist_ok=True)
    return d


def backup_config(agent_name: str, config_path: Path) -> str:
    """Copy config file to unified backup directory. Returns backup path or empty string."""
    if not config_path.exists():
        return ""
    backup_dir = get_backup_dir(agent_name)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = config_path.suffix
    b = backup_dir / f"config_{ts}{suffix}"
    shutil.copy2(config_path, b)
    return str(b)
