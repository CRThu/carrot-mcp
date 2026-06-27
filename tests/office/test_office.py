"""Tests for Carrot MCP Office Server."""

import os
import tempfile

import pytest

from carrot_mcp_office.server import mcp, version
from carrot_mcp_office.excel import (
    workbook_metadata,
    workbook_search,
    create_sheet,
    rename_sheet,
    delete_sheet,
    insert_rows,
    delete_rows,
    insert_columns,
    delete_columns,
    read_range,
    write_range,
    copy_range,
    delete_range,
    read_chart,
    write_chart,
    format_range,
)
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
    insert_image,
    delete_image,
)


@pytest.fixture
def xlsx_path():
    path = os.path.join(tempfile.gettempdir(), "test_office.xlsx")
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def docx_path():
    path = os.path.join(tempfile.gettempdir(), "test_office.docx")
    yield path
    if os.path.exists(path):
        os.unlink(path)


def test_version():
    result = version()
    assert result["status"] == "ok"
    assert result["name"] == "carrot-mcp-office"
    assert isinstance(result["version"], str)


def test_mcp_server_name():
    assert mcp.name == "carrot-mcp-office"


def test_mcp_tools_registered():
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "version" in tool_names
    assert "workbook_metadata" in tool_names
    assert "inspect" in tool_names


# ==================== Excel Tests ====================


def test_create_sheet_new_file(xlsx_path):
    result = create_sheet(xlsx_path, "Sheet1")
    assert result["status"] == "ok"
    assert result["sheet"] == "Sheet1"
    assert os.path.exists(xlsx_path)


def test_create_sheet_existing_file(xlsx_path):
    create_sheet(xlsx_path, "Sheet1")
    result = create_sheet(xlsx_path, "Sheet2")
    assert result["status"] == "ok"
    meta = workbook_metadata(xlsx_path)
    assert "Sheet1" in meta["sheets"]
    assert "Sheet2" in meta["sheets"]


def test_create_sheet_duplicate_name(xlsx_path):
    create_sheet(xlsx_path, "Sheet1")
    result = create_sheet(xlsx_path, "Sheet1")
    assert result["status"] == "error"
    assert "already exists" in result["message"]


def test_workbook_metadata(xlsx_path):
    create_sheet(xlsx_path, "Data")
    result = workbook_metadata(xlsx_path)
    assert result["status"] == "ok"
    assert "Data" in result["sheets"]


def test_workbook_metadata_nonexistent():
    result = workbook_metadata("nonexistent.xlsx")
    assert result["status"] == "error"


def test_rename_sheet(xlsx_path):
    create_sheet(xlsx_path, "OldName")
    result = rename_sheet(xlsx_path, "OldName", "NewName")
    assert result["status"] == "ok"
    meta = workbook_metadata(xlsx_path)
    assert "NewName" in meta["sheets"]
    assert "OldName" not in meta["sheets"]


def test_rename_sheet_not_found(xlsx_path):
    create_sheet(xlsx_path, "Sheet1")
    result = rename_sheet(xlsx_path, "Nonexistent", "NewName")
    assert result["status"] == "error"
    assert "not found" in result["message"]


def test_delete_sheet(xlsx_path):
    create_sheet(xlsx_path, "Sheet1")
    create_sheet(xlsx_path, "Sheet2")
    result = delete_sheet(xlsx_path, "Sheet1")
    assert result["status"] == "ok"
    meta = workbook_metadata(xlsx_path)
    assert "Sheet1" not in meta["sheets"]


def test_delete_last_sheet(xlsx_path):
    create_sheet(xlsx_path, "Sheet1")
    delete_sheet(xlsx_path, "Sheet")
    result = delete_sheet(xlsx_path, "Sheet1")
    assert result["status"] == "error"
    assert "last sheet" in result["message"]


def test_write_read_range(xlsx_path):
    create_sheet(xlsx_path, "Data")
    write_range(xlsx_path, "Data", "A1", [["Name", "Score"], ["Alice", 95], ["Bob", 87]])
    result = read_range(xlsx_path, "Data", "A1", "B3")
    assert result["status"] == "ok"
    assert result["data"] == [["Name", "Score"], ["Alice", 95], ["Bob", 87]]


def test_write_range_overwrite_protection(xlsx_path):
    create_sheet(xlsx_path, "Data")
    write_range(xlsx_path, "Data", "A1", [["Original"]])
    result = write_range(xlsx_path, "Data", "A1", [["Overwritten"]])
    assert result["status"] == "error"
    assert "overwrite" in result["message"].lower()
    val = read_range(xlsx_path, "Data", "A1")
    assert val["value"] == "Original"


def test_write_range_overwrite_allowed(xlsx_path):
    create_sheet(xlsx_path, "Data")
    write_range(xlsx_path, "Data", "A1", [["Original"]])
    result = write_range(xlsx_path, "Data", "A1", [["Overwritten"]], overwrite=True)
    assert result["status"] == "ok"
    val = read_range(xlsx_path, "Data", "A1")
    assert val["value"] == "Overwritten"


def test_write_range_backup(xlsx_path):
    create_sheet(xlsx_path, "Data")
    write_range(xlsx_path, "Data", "A1", [["Original"]])
    orig_size = os.path.getsize(xlsx_path)
    write_range(xlsx_path, "Data", "A1", [["New"]], overwrite=True, backup=True)
    bak_path = xlsx_path + ".bak"
    assert os.path.exists(bak_path)
    bak_size = os.path.getsize(bak_path)
    assert bak_size == orig_size


def test_copy_range_overwrite_protection(xlsx_path):
    create_sheet(xlsx_path, "Data")
    write_range(xlsx_path, "Data", "A1", [["Source"]])
    write_range(xlsx_path, "Data", "C1", [["Target"]])
    result = copy_range(xlsx_path, "Data", "A1", "A1", "C1")
    assert result["status"] == "error"
    assert "overwrite" in result["message"].lower()


def test_copy_range_overwrite_allowed(xlsx_path):
    create_sheet(xlsx_path, "Data")
    write_range(xlsx_path, "Data", "A1", [["Source"]])
    write_range(xlsx_path, "Data", "C1", [["Target"]])
    result = copy_range(xlsx_path, "Data", "A1", "A1", "C1", overwrite=True)
    assert result["status"] == "ok"
    val = read_range(xlsx_path, "Data", "C1")
    assert val["value"] == "Source"


def test_delete_sheet_backup(xlsx_path):
    create_sheet(xlsx_path, "Sheet1")
    create_sheet(xlsx_path, "Sheet2")
    delete_sheet(xlsx_path, "Sheet1", backup=True)
    assert os.path.exists(xlsx_path + ".bak")


def test_delete_rows_backup(xlsx_path):
    create_sheet(xlsx_path, "Data")
    write_range(xlsx_path, "Data", "A1", [["A"], ["B"], ["C"]])
    delete_rows(xlsx_path, "Data", 2, 1, backup=True)
    assert os.path.exists(xlsx_path + ".bak")


def test_word_backup(docx_path):
    insert_para(docx_path, "Original")
    modify_para(docx_path, 0, "Modified", backup=True)
    assert os.path.exists(docx_path + ".bak")


def test_word_delete_backup(docx_path):
    insert_para(docx_path, "First")
    insert_para(docx_path, "Second")
    delete_para(docx_path, 0, backup=True)
    assert os.path.exists(docx_path + ".bak")


def test_read_single_cell(xlsx_path):
    create_sheet(xlsx_path, "Data")
    write_range(xlsx_path, "Data", "A1", [["Hello"]])
    result = read_range(xlsx_path, "Data", "A1")
    assert result["status"] == "ok"
    assert result["value"] == "Hello"


def test_read_range_nonexistent_sheet(xlsx_path):
    create_sheet(xlsx_path, "Data")
    result = read_range(xlsx_path, "Nonexistent", "A1")
    assert result["status"] == "error"
    assert "not found" in result["message"]


def test_insert_delete_rows(xlsx_path):
    create_sheet(xlsx_path, "Data")
    write_range(xlsx_path, "Data", "A1", [["A"], ["B"], ["C"]])
    insert_rows(xlsx_path, "Data", 2, 1)
    result = read_range(xlsx_path, "Data", "A1", "A4")
    assert result["status"] == "ok"
    assert result["data"] == [["A"], [None], ["B"], ["C"]]


def test_insert_delete_columns(xlsx_path):
    create_sheet(xlsx_path, "Data")
    write_range(xlsx_path, "Data", "A1", [["A", "B"]])
    insert_columns(xlsx_path, "Data", 2, 1)
    result = read_range(xlsx_path, "Data", "A1", "C1")
    assert result["status"] == "ok"
    assert result["data"] == [["A", None, "B"]]


def test_copy_range(xlsx_path):
    create_sheet(xlsx_path, "Data")
    write_range(xlsx_path, "Data", "A1", [["X", "Y"]])
    copy_range(xlsx_path, "Data", "A1", "B1", "D1")
    result = read_range(xlsx_path, "Data", "D1", "E1")
    assert result["status"] == "ok"
    assert result["data"] == [["X", "Y"]]


def test_delete_range(xlsx_path):
    create_sheet(xlsx_path, "Data")
    write_range(xlsx_path, "Data", "A1", [["X", "Y"]])
    delete_range(xlsx_path, "Data", "A1", "B1")
    result = read_range(xlsx_path, "Data", "A1", "B1")
    assert result["status"] == "ok"
    assert result["data"] == [[None, None]]


def test_format_range(xlsx_path):
    create_sheet(xlsx_path, "Data")
    write_range(xlsx_path, "Data", "A1", [["Test"]])
    result = format_range(xlsx_path, "Data", "A1", "A1", bold=True, font_size=14)
    assert result["status"] == "ok"


def test_format_range_invalid_alignment(xlsx_path):
    create_sheet(xlsx_path, "Data")
    result = format_range(xlsx_path, "Data", "A1", "A1", alignment="invalid")
    assert result["status"] == "error"
    assert "Invalid alignment" in result["message"]


def test_format_range_merge(xlsx_path):
    create_sheet(xlsx_path, "Data")
    result = format_range(xlsx_path, "Data", "A1", "B2", merge=True)
    assert result["status"] == "ok"


def test_workbook_search(xlsx_path):
    create_sheet(xlsx_path, "Data")
    write_range(xlsx_path, "Data", "A1", [["Apple"], ["Banana"], ["Cherry"]])
    result = workbook_search(xlsx_path, "Data", "ana")
    assert result["status"] == "ok"
    assert result["count"] == 1
    assert result["results"][0]["cell"] == "A2"


def test_workbook_search_no_results(xlsx_path):
    create_sheet(xlsx_path, "Data")
    write_range(xlsx_path, "Data", "A1", [["Apple"]])
    result = workbook_search(xlsx_path, "Data", "xyz")
    assert result["status"] == "ok"
    assert result["count"] == 0


def test_write_chart(xlsx_path):
    create_sheet(xlsx_path, "Data")
    write_range(xlsx_path, "Data", "A1", [["Month", "Sales"], ["Jan", 100], ["Feb", 200]])
    result = write_chart(xlsx_path, "Data", "bar", "A1:B3", "D1", title="Sales")
    assert result["status"] == "ok"


def test_write_chart_invalid_type(xlsx_path):
    create_sheet(xlsx_path, "Data")
    result = write_chart(xlsx_path, "Data", "invalid", "A1:B3", "D1")
    assert result["status"] == "error"
    assert "Unknown chart type" in result["message"]


def test_read_chart(xlsx_path):
    create_sheet(xlsx_path, "Data")
    write_range(xlsx_path, "Data", "A1", [["Month", "Sales"], ["Jan", 100]])
    write_chart(xlsx_path, "Data", "bar", "A1:B2", "D1", title="Sales")
    result = read_chart(xlsx_path, "Data")
    assert result["status"] == "ok"
    assert result["count"] == 1


# ==================== Word Tests ====================


def test_insert_para_new_file(docx_path):
    result = insert_para(docx_path, "Hello World")
    assert result["status"] == "ok"
    assert result["text"] == "Hello World"
    assert os.path.exists(docx_path)


def test_insert_para_at_index(docx_path):
    insert_para(docx_path, "First")
    insert_para(docx_path, "Third")
    insert_para(docx_path, "Second", index=1)
    result = word_inspect(docx_path)
    assert result["status"] == "ok"
    texts = [p["text"] for p in result["paragraphs"]]
    assert texts == ["First", "Second", "Third"]


def test_inspect(docx_path):
    insert_para(docx_path, "Hello")
    insert_table(docx_path, 2, 2)
    result = word_inspect(docx_path)
    assert result["status"] == "ok"
    assert result["paragraph_count"] >= 1
    assert result["table_count"] == 1


def test_modify_para(docx_path):
    insert_para(docx_path, "Original")
    result = modify_para(docx_path, 0, "Modified")
    assert result["status"] == "ok"
    assert result["old_text"] == "Original"
    assert result["new_text"] == "Modified"


def test_modify_para_out_of_range(docx_path):
    insert_para(docx_path, "Hello")
    result = modify_para(docx_path, 5, "Text")
    assert result["status"] == "error"
    assert "out of range" in result["message"]


def test_format_para(docx_path):
    insert_para(docx_path, "Hello")
    result = format_para(docx_path, 0, bold=True, italic=True, alignment="center")
    assert result["status"] == "ok"


def test_format_para_invalid_alignment(docx_path):
    insert_para(docx_path, "Hello")
    result = format_para(docx_path, 0, alignment="invalid")
    assert result["status"] == "error"
    assert "Invalid alignment" in result["message"]


def test_delete_para(docx_path):
    insert_para(docx_path, "First")
    insert_para(docx_path, "Second")
    result = delete_para(docx_path, 0)
    assert result["status"] == "ok"
    info = word_inspect(docx_path)
    assert info["paragraph_count"] == 1


def test_delete_para_out_of_range(docx_path):
    insert_para(docx_path, "Hello")
    result = delete_para(docx_path, 5)
    assert result["status"] == "error"
    assert "out of range" in result["message"]


def test_insert_table(docx_path):
    result = insert_table(docx_path, 2, 3, [["A", "B", "C"], ["1", "2", "3"]])
    assert result["status"] == "ok"
    assert result["rows"] == 2
    assert result["cols"] == 3


def test_insert_table_dimension_mismatch(docx_path):
    result = insert_table(docx_path, 2, 2, [["A", "B", "C"]])
    assert result["status"] == "error"
    assert "dimensions" in result["message"]


def test_modify_table(docx_path):
    insert_table(docx_path, 2, 2)
    result = modify_table(docx_path, 0, 0, 0, "Hello")
    assert result["status"] == "ok"
    assert result["new_text"] == "Hello"


def test_modify_table_out_of_range(docx_path):
    insert_table(docx_path, 2, 2)
    result = modify_table(docx_path, 5, 0, 0, "Text")
    assert result["status"] == "error"
    assert "out of range" in result["message"]


def test_format_table(docx_path):
    insert_table(docx_path, 2, 2)
    result = format_table(docx_path, 0, style="Table Grid")
    assert result["status"] == "ok"


def test_format_table_invalid_style(docx_path):
    insert_table(docx_path, 2, 2)
    result = format_table(docx_path, 0, style="Nonexistent Style")
    assert result["status"] == "error"
    assert "not found" in result["message"]


def test_delete_table(docx_path):
    insert_table(docx_path, 2, 2)
    result = delete_table(docx_path, 0)
    assert result["status"] == "ok"
    info = word_inspect(docx_path)
    assert info["table_count"] == 0


def test_delete_table_out_of_range(docx_path):
    insert_para(docx_path, "Placeholder")
    result = delete_table(docx_path, 0)
    assert result["status"] == "error"
    assert "out of range" in result["message"]
