"""PDF cache management.

Storage:
    <hash>.json       — page data, TOC, metadata
    <hash>_tasks.json — task progress (separate, transient)
"""

import copy
import hashlib
import json
import os
import threading
import time

MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def _get_base_dir() -> str:
    """Return base cache directory: %APPDATA%/carrot-mcp/pdf or ~/.local/share/carrot-mcp/pdf."""
    base = os.environ.get("APPDATA", os.path.expanduser("~/.local/share"))
    return os.path.join(base, "carrot-mcp", "pdf")


def _pdf_hash(pdf_path: str) -> str:
    """Return MD5 hex digest of the normalized PDF path (for cache file naming)."""
    return hashlib.md5(pdf_path.encode()).hexdigest()


def get_cache_path(pdf_path: str) -> str:
    """Return absolute path to the JSON cache file for the given PDF."""
    return os.path.join(_get_base_dir(), f"{_pdf_hash(pdf_path)}.json")


def get_tasks_path(pdf_path: str) -> str:
    """Return absolute path to the tasks JSON file for the given PDF."""
    return os.path.join(_get_base_dir(), f"{_pdf_hash(pdf_path)}_tasks.json")


_lock = threading.Lock()
_mem_cache: dict[str, dict] = {}
_mem_tasks: dict[str, dict] = {}


def load_cache(pdf_path: str) -> dict:
    """Load cached PDF data (TOC, pages, metadata). Returns a deep copy to prevent mutation.

    Lookup order: in-memory cache → disk JSON → default structure.
    """
    key = get_cache_path(pdf_path)
    with _lock:
        if key in _mem_cache:
            return copy.deepcopy(_mem_cache[key])

    data = {
        "name": os.path.basename(pdf_path),
        "size": os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0,
        "path": pdf_path,
        "total_pages": 0,
        "toc": [],
        "pages": {},
    }
    if os.path.exists(key):
        try:
            with open(key, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    with _lock:
        _mem_cache[key] = data
    return copy.deepcopy(data)


def save_cache(pdf_path: str, data: dict):
    """Persist PDF data to in-memory cache and disk JSON (thread-safe)."""
    key = get_cache_path(pdf_path)
    data_copy = copy.deepcopy(data)
    with _lock:
        _mem_cache[key] = data_copy
    os.makedirs(os.path.dirname(key), exist_ok=True)
    with open(key, "w", encoding="utf-8") as f:
        json.dump(data_copy, f, ensure_ascii=False, indent=2)


def load_tasks(pdf_path: str) -> dict:
    """Load background task progress data. Returns a deep copy to prevent mutation.

    Lookup order: in-memory cache → disk JSON → empty dict.
    """
    key = get_tasks_path(pdf_path)
    with _lock:
        if key in _mem_tasks:
            return copy.deepcopy(_mem_tasks[key])

    data = {}
    if os.path.exists(key):
        try:
            with open(key, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    with _lock:
        _mem_tasks[key] = data
    return copy.deepcopy(data)


def save_tasks(pdf_path: str, data: dict):
    """Persist task data to in-memory cache and disk JSON (thread-safe)."""
    key = get_tasks_path(pdf_path)
    data_copy = copy.deepcopy(data)
    with _lock:
        _mem_tasks[key] = data_copy
    os.makedirs(os.path.dirname(key), exist_ok=True)
    with open(key, "w", encoding="utf-8") as f:
        json.dump(data_copy, f, ensure_ascii=False, indent=2)


def parse_page_range(pages_str: str) -> list[int]:
    """Parse a page range string like '1-5,8,10-12' into a sorted list of unique 1-based page numbers.

    Raises ValueError for invalid ranges, non-positive numbers, or start > end.
    """
    result = []
    for part in pages_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start_int, end_int = int(start), int(end)
            if start_int < 1 or end_int < 1:
                raise ValueError(f"Page numbers must be >= 1, got: {part}")
            if start_int > end_int:
                raise ValueError(f"Invalid range: {part} (start > end)")
            result.extend(range(start_int, end_int + 1))
        else:
            val = int(part)
            if val < 1:
                raise ValueError(f"Page numbers must be >= 1, got: {val}")
            result.append(val)
    return sorted(set(result))


def make_task_id(pdf_path: str) -> str:
    """Generate a task ID from the first 8 chars of the PDF path hash + current timestamp."""
    pdf_hash = hashlib.md5(pdf_path.encode()).hexdigest()[:8]
    return f"{pdf_hash}_{int(time.time())}"
