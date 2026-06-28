"""PDF cache management.

Storage:
    <hash>.json       — page data, TOC, metadata
    <hash>_tasks.json — task progress (separate, transient)
"""

import hashlib
import json
import os
import threading
import time


def _get_base_dir() -> str:
    base = os.environ.get("APPDATA", os.path.expanduser("~/.local/share"))
    return os.path.join(base, "carrot-mcp", "pdf")


def _pdf_hash(pdf_path: str) -> str:
    return hashlib.md5(pdf_path.encode()).hexdigest()


def get_cache_path(pdf_path: str) -> str:
    return os.path.join(_get_base_dir(), f"{_pdf_hash(pdf_path)}.json")


def get_tasks_path(pdf_path: str) -> str:
    return os.path.join(_get_base_dir(), f"{_pdf_hash(pdf_path)}_tasks.json")


# In-memory cache with thread lock
_lock = threading.Lock()
_mem_cache: dict[str, dict] = {}
_mem_tasks: dict[str, dict] = {}


def load_cache(pdf_path: str) -> dict:
    key = get_cache_path(pdf_path)
    with _lock:
        if key in _mem_cache:
            return _mem_cache[key]

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
    return data


def save_cache(pdf_path: str, data: dict):
    key = get_cache_path(pdf_path)
    with _lock:
        _mem_cache[key] = data
        os.makedirs(os.path.dirname(key), exist_ok=True)
        with open(key, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def load_tasks(pdf_path: str) -> dict:
    key = get_tasks_path(pdf_path)
    with _lock:
        if key in _mem_tasks:
            return _mem_tasks[key]

    data = {}
    if os.path.exists(key):
        try:
            with open(key, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    with _lock:
        _mem_tasks[key] = data
    return data


def save_tasks(pdf_path: str, data: dict):
    key = get_tasks_path(pdf_path)
    with _lock:
        _mem_tasks[key] = data
        os.makedirs(os.path.dirname(key), exist_ok=True)
        with open(key, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def parse_page_range(pages_str: str) -> list[int]:
    result = []
    for part in pages_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            result.extend(range(int(start), int(end) + 1))
        else:
            result.append(int(part))
    return sorted(set(result))


def make_task_id(pdf_path: str) -> str:
    pdf_hash = hashlib.md5(pdf_path.encode()).hexdigest()[:8]
    return f"{pdf_hash}_{int(time.time())}"
