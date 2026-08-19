"""Tests for internal formatting utilities."""

from carrot_mcp_office._format import render_table_markdown, parse_index_range


def test_render_table_markdown_empty():
    assert render_table_markdown([]) == ""
    assert render_table_markdown([[]]) == ""


def test_render_table_markdown_basic():
    data = [
        ["Col1", "Col2"],
        ["Val1", "Val2"],
    ]
    md = render_table_markdown(data)
    assert "| Col1 | Col2 |" in md
    assert "| --- | --- |" in md
    assert "| Val1 | Val2 |" in md


def test_render_table_markdown_escaping_and_none():
    data = [
        ["Header | Pipe", "Newline\nText"],
        [None, 123],
    ]
    md = render_table_markdown(data)
    assert r"Header \| Pipe" in md
    assert "Newline Text" in md
    assert "|  | 123 |" in md


def test_parse_index_range():
    assert parse_index_range(None, 10) == []
    assert parse_index_range(3, 10) == [3]
    assert parse_index_range(15, 10) == []
    assert parse_index_range("0-3", 10) == [0, 1, 2, 3]
    assert parse_index_range("0, 2, 4-6", 10) == [0, 2, 4, 5, 6]
    assert parse_index_range([0, "2-4", 6], 10) == [0, 2, 3, 4, 6]
    assert parse_index_range([5, "0-2"], 10) == [0, 1, 2, 5]
