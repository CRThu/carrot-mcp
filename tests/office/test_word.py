"""Tests for Word tools."""

import os
import shutil
import tempfile

from carrot_mcp_office.word import (
    inspect as word_inspect,
    insert_para,
    modify_para,
    format_para,
    delete_para,
    insert_table,
    modify_table,
    format_table,
    delete_table,
)


def _cleanup(original_path):
    from carrot_mcp_office.backup import _mirror_path
    mirror = _mirror_path(original_path)
    if mirror.parent.exists():
        shutil.rmtree(mirror.parent, ignore_errors=True)


def _docx():
    return os.path.join(tempfile.gettempdir(), "test_office.docx")


def test_insert_para_new_file():
    path = _docx()
    try:
        result = insert_para(path, "Hello World")
        assert result["status"] == "ok"
        assert result["text"] == "Hello World"
        assert result["version"] >= 1
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_insert_para_at_index():
    path = _docx()
    try:
        insert_para(path, "First")
        insert_para(path, "Third")
        insert_para(path, "Second", index=1)
        result = word_inspect(path)
        assert result["status"] == "ok"
        texts = [p["text"] for p in result["paragraphs"]]
        assert texts == ["First", "Second", "Third"]
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_inspect():
    path = _docx()
    try:
        insert_para(path, "Hello")
        insert_table(path, 2, 2)
        result = word_inspect(path)
        assert result["status"] == "ok"
        assert result["paragraph_count"] >= 1
        assert result["table_count"] == 1
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_modify_para():
    path = _docx()
    try:
        insert_para(path, "Original")
        result = modify_para(path, 0, "Modified")
        assert result["status"] == "ok"
        assert result["old_text"] == "Original"
        assert result["new_text"] == "Modified"
        assert result["version"] >= 1
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_modify_para_out_of_range():
    path = _docx()
    try:
        insert_para(path, "Hello")
        result = modify_para(path, 5, "Text")
        assert result["status"] == "error"
        assert "out of range" in result["message"]
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_format_para():
    path = _docx()
    try:
        insert_para(path, "Hello")
        result = format_para(path, 0, bold=True, italic=True, alignment="center")
        assert result["status"] == "ok"
        assert result["version"] >= 1
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_format_para_invalid_alignment():
    path = _docx()
    try:
        insert_para(path, "Hello")
        result = format_para(path, 0, alignment="invalid")
        assert result["status"] == "error"
        assert "Invalid alignment" in result["message"]
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_delete_para():
    path = _docx()
    try:
        insert_para(path, "First")
        insert_para(path, "Second")
        result = delete_para(path, 0)
        assert result["status"] == "ok"
        assert result["version"] >= 1
        info = word_inspect(path)
        assert info["paragraph_count"] == 1
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_delete_para_out_of_range():
    path = _docx()
    try:
        insert_para(path, "Hello")
        result = delete_para(path, 5)
        assert result["status"] == "error"
        assert "out of range" in result["message"]
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_insert_table():
    path = _docx()
    try:
        result = insert_table(path, 2, 3, [["A", "B", "C"], ["1", "2", "3"]])
        assert result["status"] == "ok"
        assert result["rows"] == 2
        assert result["cols"] == 3
        assert result["version"] >= 1
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_insert_table_dimension_mismatch():
    path = _docx()
    try:
        result = insert_table(path, 2, 2, [["A", "B", "C"]])
        assert result["status"] == "error"
        assert "dimensions" in result["message"]
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_modify_table():
    path = _docx()
    try:
        insert_table(path, 2, 2)
        result = modify_table(path, 0, 0, 0, "Hello")
        assert result["status"] == "ok"
        assert result["new_text"] == "Hello"
        assert result["version"] >= 1
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_modify_table_out_of_range():
    path = _docx()
    try:
        insert_table(path, 2, 2)
        result = modify_table(path, 5, 0, 0, "Text")
        assert result["status"] == "error"
        assert "out of range" in result["message"]
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_format_table():
    path = _docx()
    try:
        insert_table(path, 2, 2)
        result = format_table(path, 0, style="Table Grid")
        assert result["status"] == "ok"
        assert result["version"] >= 1
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_format_table_invalid_style():
    path = _docx()
    try:
        insert_table(path, 2, 2)
        result = format_table(path, 0, style="Nonexistent Style")
        assert result["status"] == "error"
        assert "not found" in result["message"]
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_delete_table():
    path = _docx()
    try:
        insert_table(path, 2, 2)
        result = delete_table(path, 0)
        assert result["status"] == "ok"
        assert result["version"] >= 1
        info = word_inspect(path)
        assert info["table_count"] == 0
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_delete_table_out_of_range():
    path = _docx()
    try:
        insert_para(path, "Placeholder")
        result = delete_table(path, 0)
        assert result["status"] == "error"
        assert "out of range" in result["message"]
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)
