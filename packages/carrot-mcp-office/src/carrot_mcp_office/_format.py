"""Internal formatting utilities for carrot-mcp-office."""

from __future__ import annotations

from typing import Any


def render_table_markdown(data: list[list[Any]]) -> str:
    """Render a 2D array into a GitHub-flavored Markdown table.

    Handles None values, escapes pipe characters, converts newlines to spaces,
    and pads columns to align nicely.
    """
    if not data:
        return ""

    normalized: list[list[str]] = []
    for row in data:
        normalized_row = [
            str(cell if cell is not None else "")
            .replace("\r\n", " ")
            .replace("\n", " ")
            .replace("|", "\\|")
            .strip()
            for cell in row
        ]
        normalized.append(normalized_row)

    num_cols = max((len(r) for r in normalized), default=0)
    if num_cols == 0:
        return ""

    for row in normalized:
        while len(row) < num_cols:
            row.append("")

    header = normalized[0]
    separator = ["---"] * num_cols
    rows = normalized[1:] if len(normalized) > 1 else []

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for r in rows:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def parse_index_range(raw: list | int | str | None, max_index: int) -> list[int]:
    """Parse index / section range specification into a sorted list of 0-based integers.

    Accepts:
      - None: returns empty list []
      - int: single index (e.g. 0 → [0]) if within [0, max_index]
      - str: range or comma-separated list (e.g. "0-4,6,8" or "0-9")
      - list: where elements can be int or range strings
    """
    if raw is None:
        return []

    if isinstance(raw, int):
        return [raw] if 0 <= raw <= max_index else []

    if isinstance(raw, str):
        raw = [raw]

    result = []
    for item in raw:
        if isinstance(item, int):
            result.append(item)
        elif isinstance(item, str):
            for part in item.split(","):
                part = part.strip()
                if not part:
                    continue
                if "-" in part and not part.startswith("-"):
                    a, b = part.split("-", 1)
                    a, b = int(a.strip()), int(b.strip())
                    result.extend(range(a, b + 1))
                else:
                    result.append(int(part))
    return sorted(set(result))
