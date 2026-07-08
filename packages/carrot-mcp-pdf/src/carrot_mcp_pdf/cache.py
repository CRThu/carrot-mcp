"""PDF cache management.

Storage:
    <hash>.json — page data, TOC, metadata
"""

import copy
import hashlib
import json
import os
import threading

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


_lock = threading.Lock()
_mem_cache: dict[str, dict] = {}


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


def parse_page_range(pages: str | int | list | None, max_page: int | None = None) -> list[int]:
    """Parse a page range specification into a sorted list of unique 1-based page numbers.

    Accepts:
        - None: returns empty list
        - int: single page number (e.g. 5 → [5])
        - str: range string like '1-5,8,10-12'
        - list: array of int/str, e.g. [1, "3-5", 8]

    Raises ValueError for invalid ranges, non-positive numbers, or start > end.
    """
    if pages is None:
        return []

    if isinstance(pages, int):
        if pages < 1:
            raise ValueError(f"Page numbers must be >= 1, got: {pages}")
        return [pages]

    if isinstance(pages, str):
        pages = [pages]

    if not isinstance(pages, list):
        raise ValueError(f"Invalid type: {type(pages)}")

    result = []
    for item in pages:
        if isinstance(item, int):
            if item < 1:
                raise ValueError(f"Page numbers must be >= 1, got: {item}")
            result.append(item)
        elif isinstance(item, str):
            for part in item.split(","):
                part = part.strip()
                if not part:
                    continue
                if "-" in part and not part.startswith("-"):
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
