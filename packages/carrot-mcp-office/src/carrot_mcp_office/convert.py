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
    import gc
    import win32com.client
    import pythoncom

    abs_path = os.path.abspath(doc_path)
    new_path = os.path.splitext(abs_path)[0] + ".docx"

    pythoncom.CoInitialize()
    word = None
    doc = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(abs_path, ReadOnly=True)
        # 16 = wdFormatXMLDocument (.docx)
        doc.SaveAs(new_path, FileFormat=16)
        return new_path
    finally:
        if doc is not None:
            try:
                doc.Close(SaveChanges=0)
            except Exception:
                pass
            doc = None
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass
            word = None
        gc.collect()
        pythoncom.CoUninitialize()


def _convert_xls_to_xlsx(xls_path: str) -> str:
    """Convert .xls to .xlsx via win32com. Returns the new .xlsx path."""
    import gc
    import win32com.client
    import pythoncom

    abs_path = os.path.abspath(xls_path)
    new_path = os.path.splitext(abs_path)[0] + ".xlsx"

    pythoncom.CoInitialize()
    excel = None
    wb = None
    try:
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        wb = excel.Workbooks.Open(abs_path, ReadOnly=True)
        # 51 = xlOpenXMLWorkbook (.xlsx)
        wb.SaveAs(new_path, FileFormat=51)
        return new_path
    finally:
        if wb is not None:
            try:
                wb.Close(SaveChanges=False)
            except Exception:
                pass
            wb = None
        if excel is not None:
            try:
                excel.Quit()
            except Exception:
                pass
            excel = None
        gc.collect()
        pythoncom.CoUninitialize()


def ensure_docx_format(path: str) -> tuple[str, str | None]:
    """Ensure the file is in .docx format.

    Returns (path, error_message). If conversion succeeds, path is the .docx path.
    If no conversion needed, path is returned as-is with None error.
    If a .docx with the same stem already exists and is newer than the .doc,
    it is reused without re-converting.
    """
    ext = Path(path).suffix.lower()
    if ext != ".doc":
        return path, None

    if not os.path.exists(path):
        return path, None

    docx_path = os.path.splitext(os.path.abspath(path))[0] + ".docx"
    if os.path.exists(docx_path) and os.path.getmtime(docx_path) >= os.path.getmtime(path):
        return docx_path, None

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
    If an .xlsx with the same stem already exists and is newer than the .xls,
    it is reused without re-converting.
    """
    ext = Path(path).suffix.lower()
    if ext != ".xls":
        return path, None

    if not os.path.exists(path):
        return path, None

    xlsx_path = os.path.splitext(os.path.abspath(path))[0] + ".xlsx"
    if os.path.exists(xlsx_path) and os.path.getmtime(xlsx_path) >= os.path.getmtime(path):
        return xlsx_path, None

    if not _has_win32com():
        return path, "Legacy .xls conversion requires pywin32 (Windows only). Install with: pip install pywin32"

    try:
        new_path = _convert_xls_to_xlsx(path)
        return new_path, None
    except Exception as e:
        return path, f"Failed to convert .xls to .xlsx: {e}"
