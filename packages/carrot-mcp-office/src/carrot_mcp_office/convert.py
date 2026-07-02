"""Legacy format conversion (.doc/.xls → .docx/.xlsx) via win32com.

Provides implicit auto-conversion for all Office tools.
"""

from __future__ import annotations

import os
from pathlib import Path


def _has_win32com() -> bool:
    """Check if win32com.client is available."""
    try:
        import win32com.client  # noqa: F401
        return True
    except ImportError:
        return False


def _convert_doc_to_docx(doc_path: str) -> str:
    """Convert .doc to .docx via win32com. Returns the new .docx path."""
    import win32com.client
    import pythoncom

    abs_path = os.path.abspath(doc_path)
    new_path = os.path.splitext(abs_path)[0] + ".docx"

    pythoncom.CoInitialize()
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(abs_path)
        # 16 = wdFormatXMLDocument (.docx)
        doc.SaveAs(new_path, FileFormat=16)
        doc.Close()
        word.Quit()
        return new_path
    finally:
        pythoncom.CoUninitialize()


def _convert_xls_to_xlsx(xls_path: str) -> str:
    """Convert .xls to .xlsx via win32com. Returns the new .xlsx path."""
    import win32com.client
    import pythoncom

    abs_path = os.path.abspath(xls_path)
    new_path = os.path.splitext(abs_path)[0] + ".xlsx"

    pythoncom.CoInitialize()
    try:
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = False
        wb = excel.Workbooks.Open(abs_path)
        # 51 = xlOpenXMLWorkbook (.xlsx)
        wb.SaveAs(new_path, FileFormat=51)
        wb.Close()
        excel.Quit()
        return new_path
    finally:
        pythoncom.CoUninitialize()


def ensure_docx_format(path: str) -> tuple[str, str | None]:
    """Ensure the file is in .docx format.

    Returns (path, error_message). If conversion succeeds, path is the .docx path.
    If no conversion needed, path is returned as-is with None error.
    """
    ext = Path(path).suffix.lower()
    if ext != ".doc":
        return path, None

    if not os.path.exists(path):
        return path, None

    if not _has_win32com():
        return path, "Legacy .doc conversion requires pywin32 (Windows only). Install with: pip install pywin32"

    try:
        new_path = _convert_doc_to_docx(path)
        return new_path, None
    except Exception as e:
        return path, f"Failed to convert .doc to .docx: {e}"


def ensure_xlsx_format(path: str) -> tuple[str, str | None]:
    """Ensure the file is in .xlsx format.

    Returns (path, error_message). If conversion succeeds, path is the .xlsx path.
    If no conversion needed, path is returned as-is with None error.
    """
    ext = Path(path).suffix.lower()
    if ext != ".xls":
        return path, None

    if not os.path.exists(path):
        return path, None

    if not _has_win32com():
        return path, "Legacy .xls conversion requires pywin32 (Windows only). Install with: pip install pywin32"

    try:
        new_path = _convert_xls_to_xlsx(path)
        return new_path, None
    except Exception as e:
        return path, f"Failed to convert .xls to .xlsx: {e}"
