"""Tests for legacy Office format conversion (convert.py)."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from carrot_mcp_office.convert import (
    _has_win32com,
    _convert_doc_to_docx,
    _convert_xls_to_xlsx,
    ensure_docx_format,
    ensure_xlsx_format,
)


# --- _has_win32com ---


def test_has_win32com():
    # Test when win32com is present / absent
    result = _has_win32com()
    assert isinstance(result, bool)


def test_has_win32com_import_error():
    with patch.dict(sys.modules, {"win32com.client": None}):
        with patch("builtins.__import__", side_effect=ImportError("No module named win32com")):
            assert _has_win32com() is False


# --- ensure_docx_format ---


def test_ensure_docx_not_doc():
    path, err = ensure_docx_format("test.docx")
    assert path == "test.docx"
    assert err is None


def test_ensure_docx_file_not_found(tmp_path):
    non_existent = str(tmp_path / "not_found.doc")
    path, err = ensure_docx_format(non_existent)
    assert path == non_existent
    assert err is None


def test_ensure_docx_reuse_existing(tmp_path):
    doc_file = tmp_path / "test.doc"
    doc_file.write_text("dummy")
    docx_file = tmp_path / "test.docx"
    docx_file.write_text("dummy docx")

    # Set docx mtime >= doc mtime
    os.utime(str(doc_file), (1000, 1000))
    os.utime(str(docx_file), (2000, 2000))

    path, err = ensure_docx_format(str(doc_file))
    assert path == str(docx_file)
    assert err is None


def test_ensure_docx_reconvert_if_doc_newer(tmp_path):
    doc_file = tmp_path / "test.doc"
    doc_file.write_text("dummy doc")
    docx_file = tmp_path / "test.docx"
    docx_file.write_text("old docx")

    # doc is newer than docx
    os.utime(str(docx_file), (1000, 1000))
    os.utime(str(doc_file), (2000, 2000))

    with patch("carrot_mcp_office.convert._has_win32com", return_value=True):
        with patch("carrot_mcp_office.convert._convert_doc_to_docx", return_value=str(docx_file)) as mock_conv:
            path, err = ensure_docx_format(str(doc_file))
            assert path == str(docx_file)
            assert err is None
            mock_conv.assert_called_once_with(str(doc_file))


def test_ensure_docx_no_win32com(tmp_path):
    doc_file = tmp_path / "test.doc"
    doc_file.write_text("dummy")

    with patch("carrot_mcp_office.convert._has_win32com", return_value=False):
        path, err = ensure_docx_format(str(doc_file))
        assert path == str(doc_file)
        assert "requires pywin32" in err


def test_ensure_docx_conversion_failure(tmp_path):
    doc_file = tmp_path / "test.doc"
    doc_file.write_text("dummy")

    with patch("carrot_mcp_office.convert._has_win32com", return_value=True):
        with patch("carrot_mcp_office.convert._convert_doc_to_docx", side_effect=Exception("Word error")):
            path, err = ensure_docx_format(str(doc_file))
            assert path == str(doc_file)
            assert "Failed to convert .doc to .docx: Word error" in err


# --- ensure_xlsx_format ---


def test_ensure_xlsx_not_xls():
    path, err = ensure_xlsx_format("test.xlsx")
    assert path == "test.xlsx"
    assert err is None


def test_ensure_xlsx_file_not_found(tmp_path):
    non_existent = str(tmp_path / "not_found.xls")
    path, err = ensure_xlsx_format(non_existent)
    assert path == non_existent
    assert err is None


def test_ensure_xlsx_reuse_existing(tmp_path):
    xls_file = tmp_path / "test.xls"
    xls_file.write_text("dummy")
    xlsx_file = tmp_path / "test.xlsx"
    xlsx_file.write_text("dummy xlsx")

    os.utime(str(xls_file), (1000, 1000))
    os.utime(str(xlsx_file), (2000, 2000))

    path, err = ensure_xlsx_format(str(xls_file))
    assert path == str(xlsx_file)
    assert err is None


def test_ensure_xlsx_reconvert_if_xls_newer(tmp_path):
    xls_file = tmp_path / "test.xls"
    xls_file.write_text("dummy xls")
    xlsx_file = tmp_path / "test.xlsx"
    xlsx_file.write_text("old xlsx")

    os.utime(str(xlsx_file), (1000, 1000))
    os.utime(str(xls_file), (2000, 2000))

    with patch("carrot_mcp_office.convert._has_win32com", return_value=True):
        with patch("carrot_mcp_office.convert._convert_xls_to_xlsx", return_value=str(xlsx_file)) as mock_conv:
            path, err = ensure_xlsx_format(str(xls_file))
            assert path == str(xlsx_file)
            assert err is None
            mock_conv.assert_called_once_with(str(xls_file))


def test_ensure_xlsx_no_win32com(tmp_path):
    xls_file = tmp_path / "test.xls"
    xls_file.write_text("dummy")

    with patch("carrot_mcp_office.convert._has_win32com", return_value=False):
        path, err = ensure_xlsx_format(str(xls_file))
        assert path == str(xls_file)
        assert "requires pywin32" in err


def test_ensure_xlsx_conversion_failure(tmp_path):
    xls_file = tmp_path / "test.xls"
    xls_file.write_text("dummy")

    with patch("carrot_mcp_office.convert._has_win32com", return_value=True):
        with patch("carrot_mcp_office.convert._convert_xls_to_xlsx", side_effect=Exception("Excel error")):
            path, err = ensure_xlsx_format(str(xls_file))
            assert path == str(xls_file)
            assert "Failed to convert .xls to .xlsx: Excel error" in err


# --- _convert_doc_to_docx and _convert_xls_to_xlsx implementation tests ---


def test_convert_doc_to_docx_mock(tmp_path):
    doc_file = tmp_path / "sample.doc"
    doc_file.write_text("dummy")

    mock_word = MagicMock()
    mock_doc = MagicMock()
    mock_word.Documents.Open.return_value = mock_doc

    mock_win32com = MagicMock()
    mock_win32com.client.DispatchEx.return_value = mock_word
    mock_pythoncom = MagicMock()

    with patch.dict(sys.modules, {"win32com": mock_win32com, "win32com.client": mock_win32com.client, "pythoncom": mock_pythoncom}):
        res = _convert_doc_to_docx(str(doc_file))
        assert res.endswith(".docx")
        mock_pythoncom.CoInitialize.assert_called_once()
        mock_win32com.client.DispatchEx.assert_called_once_with("Word.Application")
        assert mock_word.Visible is False
        assert mock_word.DisplayAlerts == 0
        mock_word.Documents.Open.assert_called_once_with(os.path.abspath(str(doc_file)), ReadOnly=True)
        mock_doc.SaveAs.assert_called_once_with(os.path.abspath(str(tmp_path / "sample.docx")), FileFormat=16)
        mock_doc.Close.assert_called_once_with(SaveChanges=0)
        mock_word.Quit.assert_called_once()
        mock_pythoncom.CoUninitialize.assert_called_once()


def test_convert_doc_to_docx_cleanup_on_error(tmp_path):
    doc_file = tmp_path / "sample.doc"
    doc_file.write_text("dummy")

    mock_word = MagicMock()
    mock_doc = MagicMock()
    mock_word.Documents.Open.return_value = mock_doc
    mock_doc.SaveAs.side_effect = RuntimeError("SaveAs failed")

    mock_win32com = MagicMock()
    mock_win32com.client.DispatchEx.return_value = mock_word
    mock_pythoncom = MagicMock()

    with patch.dict(sys.modules, {"win32com": mock_win32com, "win32com.client": mock_win32com.client, "pythoncom": mock_pythoncom}):
        with pytest.raises(RuntimeError, match="SaveAs failed"):
            _convert_doc_to_docx(str(doc_file))

        mock_doc.Close.assert_called_once_with(SaveChanges=0)
        mock_word.Quit.assert_called_once()
        mock_pythoncom.CoUninitialize.assert_called_once()


def test_convert_xls_to_xlsx_mock(tmp_path):
    xls_file = tmp_path / "sample.xls"
    xls_file.write_text("dummy")

    mock_excel = MagicMock()
    mock_wb = MagicMock()
    mock_excel.Workbooks.Open.return_value = mock_wb

    mock_win32com = MagicMock()
    mock_win32com.client.DispatchEx.return_value = mock_excel
    mock_pythoncom = MagicMock()

    with patch.dict(sys.modules, {"win32com": mock_win32com, "win32com.client": mock_win32com.client, "pythoncom": mock_pythoncom}):
        res = _convert_xls_to_xlsx(str(xls_file))
        assert res.endswith(".xlsx")
        mock_pythoncom.CoInitialize.assert_called_once()
        mock_win32com.client.DispatchEx.assert_called_once_with("Excel.Application")
        assert mock_excel.Visible is False
        assert mock_excel.DisplayAlerts is False
        mock_excel.Workbooks.Open.assert_called_once_with(os.path.abspath(str(xls_file)), ReadOnly=True)
        mock_wb.SaveAs.assert_called_once_with(os.path.abspath(str(tmp_path / "sample.xlsx")), FileFormat=51)
        mock_wb.Close.assert_called_once_with(SaveChanges=False)
        mock_excel.Quit.assert_called_once()
        mock_pythoncom.CoUninitialize.assert_called_once()


def test_convert_xls_to_xlsx_cleanup_on_error(tmp_path):
    xls_file = tmp_path / "sample.xls"
    xls_file.write_text("dummy")

    mock_excel = MagicMock()
    mock_wb = MagicMock()
    mock_excel.Workbooks.Open.return_value = mock_wb
    mock_wb.SaveAs.side_effect = RuntimeError("SaveAs failed")

    mock_win32com = MagicMock()
    mock_win32com.client.DispatchEx.return_value = mock_excel
    mock_pythoncom = MagicMock()

    with patch.dict(sys.modules, {"win32com": mock_win32com, "win32com.client": mock_win32com.client, "pythoncom": mock_pythoncom}):
        with pytest.raises(RuntimeError, match="SaveAs failed"):
            _convert_xls_to_xlsx(str(xls_file))

        mock_wb.Close.assert_called_once_with(SaveChanges=False)
        mock_excel.Quit.assert_called_once()
        mock_pythoncom.CoUninitialize.assert_called_once()
