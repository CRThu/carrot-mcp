"""Versioned backup system for carrot-mcp-office.

Backups are stored in %APPDATA%/carrot-mcp/office/ with mirrored directory structure.
Each file gets versioned copies (filename_v001.ext, _v002.ext, ...) and a _versions.json metadata file.

Configuration via environment variables:
  CARROT_MCP_BACKUP_MAX_VERSIONS  — max versions to keep (default: 100)
  CARROT_MCP_BACKUP_MAX_AGE_DAYS  — days before auto-delete (default: 14)
  CARROT_MCP_BACKUP_ROOT          — override backup root directory
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

MAX_VERSIONS = int(os.environ.get("CARROT_MCP_BACKUP_MAX_VERSIONS", "100"))
MAX_AGE_DAYS = int(os.environ.get("CARROT_MCP_BACKUP_MAX_AGE_DAYS", "14"))


@dataclass
class VersionEntry:
    number: int
    file: str
    tool: str
    timestamp: str
    original_size: int


@dataclass
class VersionsMeta:
    versions: list[VersionEntry] = field(default_factory=list)
    max_versions: int = field(default_factory=lambda: MAX_VERSIONS)


def backup_root() -> Path:
    """Return the backup root directory, creating it if needed."""
    override = os.environ.get("CARROT_MCP_BACKUP_ROOT")
    if override:
        root = Path(override)
    elif os.name == "nt":
        base = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        root = Path(base) / "carrot-mcp" / "office"
    else:
        base = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
        root = Path(base) / "carrot-mcp" / "office"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _mirror_path(original: str) -> Path:
    """Map original file path to backup directory structure.

    D:\\docs\\reports\\file.xlsx -> backup_root/D/docs/reports/file (no ext)
    """
    normalized = original.replace("\\", "/")
    p = Path(normalized)
    root = backup_root()
    drive = p.drive.rstrip(":") if p.drive else "_"
    parts = list(p.parts[1:])
    stem = p.stem
    if len(parts) > 1:
        return root / drive / Path(*parts[:-1]) / stem
    return root / drive / stem


def _versions_json_path(original: str) -> Path:
    """Return the _versions.json path for a given original file."""
    return _mirror_path(original).parent / "_versions.json"


def _load_versions(original: str) -> VersionsMeta:
    """Load or create empty version metadata for a file."""
    jp = _versions_json_path(original)
    if jp.exists():
        try:
            data = json.loads(jp.read_text(encoding="utf-8"))
            entries = [VersionEntry(**v) for v in data.get("versions", [])]
            return VersionsMeta(versions=entries, max_versions=data.get("max_versions", MAX_VERSIONS))
        except (json.JSONDecodeError, TypeError):
            pass
    return VersionsMeta()


def _save_versions(original: str, meta: VersionsMeta) -> None:
    """Write version metadata to JSON."""
    jp = _versions_json_path(original)
    jp.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "versions": [asdict(v) for v in meta.versions],
        "max_versions": meta.max_versions,
    }
    jp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _next_version_number(meta: VersionsMeta) -> int:
    """Get the next version number."""
    if not meta.versions:
        return 1
    return max(v.number for v in meta.versions) + 1


def _versioned_filename(original: str, version: int) -> str:
    """Generate versioned filename: file_v001.xlsx"""
    p = Path(original)
    return f"{p.stem}_v{version:03d}{p.suffix}"


def _prune_versions(meta: VersionsMeta) -> list[VersionEntry]:
    """Return versions that should be deleted."""
    now = datetime.now(timezone.utc)
    to_delete: list[VersionEntry] = []
    remaining: list[VersionEntry] = []

    for v in meta.versions:
        try:
            ts = datetime.fromisoformat(v.timestamp)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if (now - ts).days > MAX_AGE_DAYS:
                to_delete.append(v)
                continue
        except (ValueError, TypeError):
            pass
        remaining.append(v)

    if len(remaining) > meta.max_versions:
        excess = len(remaining) - meta.max_versions
        to_delete.extend(remaining[:excess])

    return to_delete


def _update_root_timestamp() -> None:
    """Update the last-modified timestamp in backup root."""
    root = backup_root()
    ts_file = root / "_last_modified.txt"
    ts_file.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")


def save_version(path: str, tool: str) -> int | None:
    """Save a versioned backup of the file. Returns the version number, or None if file doesn't exist."""
    if not os.path.exists(path):
        return None

    meta = _load_versions(path)
    ver = _next_version_number(meta)
    fname = _versioned_filename(path, ver)
    mirror = _mirror_path(path)
    mirror.mkdir(parents=True, exist_ok=True)
    dest = mirror / fname

    shutil.copy2(path, dest)

    entry = VersionEntry(
        number=ver,
        file=fname,
        tool=tool,
        timestamp=datetime.now(timezone.utc).isoformat(),
        original_size=os.path.getsize(path),
    )
    meta.versions.append(entry)

    to_delete = _prune_versions(meta)
    for v in to_delete:
        old_file = mirror / v.file
        if old_file.exists():
            old_file.unlink()
        meta.versions.remove(v)

    _save_versions(path, meta)
    _update_root_timestamp()

    return ver


def list_versions(path: str) -> list[VersionEntry]:
    """List all backup versions for a file."""
    meta = _load_versions(path)
    return list(meta.versions)


def restore_version(path: str, version: int) -> str:
    """Restore a specific version to the original path. Returns the restored path."""
    meta = _load_versions(path)
    entry = None
    for v in meta.versions:
        if v.number == version:
            entry = v
            break
    if entry is None:
        raise ValueError(f"Version {version} not found for {path}")

    mirror = _mirror_path(path)
    src = mirror / entry.file
    if not src.exists():
        raise FileNotFoundError(f"Backup file not found: {src}")

    shutil.copy2(src, path)
    return path
