"""Word tools for carrot-mcp-office using python-docx."""

from __future__ import annotations

import os

from docx import Document
from docx.shared import Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from carrot_mcp_office._mcp import mcp
from carrot_mcp_office.backup import save_version
from carrot_mcp_office.convert import ensure_docx_format


def _open_or_create_document(path: str) -> Document:
    """Open existing document or create a new one."""
    if os.path.exists(path):
        return Document(path)
    doc = Document()
    doc.save(path)
    return Document(path)


def _handle_docx(path: str) -> tuple[str, dict | None]:
    """Ensure docx format, return (resolved_path, error_or_none)."""
    resolved, err = ensure_docx_format(path)
    if err:
        return path, {"status": "error", "message": err}
    return resolved, None


def _save_and_return(path: str, tool: str, result: dict) -> dict:
    """Add version to result and save backup."""
    ver = save_version(path, tool)
    if ver is not None:
        result["version"] = ver
    return result


@mcp.tool()
def inspect(path: str) -> dict:
    """Inspect document structure (paragraphs, tables, images, styles).

    Args:
        path: Absolute path to the .docx file.
    """
    try:
        doc = Document(path)
        paragraphs = [{"index": i, "text": p.text[:100], "style": p.style.name} for i, p in enumerate(doc.paragraphs)]
        tables = [{"index": i, "rows": len(t.rows), "cols": len(t.columns)} for i, t in enumerate(doc.tables)]
        image_count = 0
        for p in doc.paragraphs:
            for run in p.runs:
                if run._element.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing"):
                    image_count += 1
        styles = list({p.style.name for p in doc.paragraphs})
        return {
            "status": "ok",
            "path": path,
            "paragraph_count": len(doc.paragraphs),
            "table_count": len(doc.tables),
            "image_count": image_count,
            "styles_used": styles,
            "paragraphs": paragraphs[:50],
            "tables": tables,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def insert_para(path: str, text: str, index: int | None = None) -> dict:
    """Insert a paragraph at the specified position.

    Args:
        path: Absolute path to the .docx file.
        text: Paragraph text content.
        index: Position (0-based) to insert at. None appends at end.
    """
    try:
        path, err = _handle_docx(path)
        if err:
            return err
        doc = _open_or_create_document(path)
        if index is None or index >= len(doc.paragraphs):
            doc.add_paragraph(text)
        else:
            ref_para = doc.paragraphs[index]
            new_para = doc.add_paragraph(text)
            ref_para._element.addprevious(new_para._element)
        doc.save(path)
        return _save_and_return(path, "insert_para", {"status": "ok", "text": text, "index": index if index is not None else len(doc.paragraphs) - 1})
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def modify_para(path: str, index: int, text: str) -> dict:
    """Modify an existing paragraph's text.

    Args:
        path: Absolute path to the .docx file.
        index: Paragraph index (0-based).
        text: New text content.
    """
    try:
        path, err = _handle_docx(path)
        if err:
            return err
        doc = Document(path)
        if index < 0 or index >= len(doc.paragraphs):
            return {"status": "error", "message": f"Paragraph index {index} out of range (0-{len(doc.paragraphs)-1})"}
        para = doc.paragraphs[index]
        old_text = para.text
        for run in para.runs:
            run.text = ""
        if para.runs:
            para.runs[0].text = text
        else:
            para.text = text
        doc.save(path)
        return _save_and_return(path, "modify_para", {"status": "ok", "index": index, "old_text": old_text, "new_text": text})
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def format_para(
    path: str,
    index: int,
    style: str | None = None,
    alignment: str | None = None,
    bold: bool | None = None,
    italic: bool | None = None,
    font_size: int | None = None,
    font_color: str | None = None,
) -> dict:
    """Format a paragraph.

    Args:
        path: Absolute path to the .docx file.
        index: Paragraph index (0-based).
        style: Style name (e.g. "Heading 1", "Normal", "Title").
        alignment: Text alignment (left, center, right, justify).
        bold: Bold text.
        italic: Italic text.
        font_size: Font size in points.
        font_color: Font color as hex string (e.g. "FF0000").
    """
    try:
        path, err = _handle_docx(path)
        if err:
            return err
        doc = Document(path)
        if index < 0 or index >= len(doc.paragraphs):
            return {"status": "error", "message": f"Paragraph index {index} out of range (0-{len(doc.paragraphs)-1})"}
        para = doc.paragraphs[index]
        if style:
            try:
                para.style = doc.styles[style]
            except KeyError:
                return {"status": "error", "message": f"Style '{style}' not found"}
        if alignment:
            align_map = {
                "left": WD_ALIGN_PARAGRAPH.LEFT,
                "center": WD_ALIGN_PARAGRAPH.CENTER,
                "right": WD_ALIGN_PARAGRAPH.RIGHT,
                "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
            }
            if alignment not in align_map:
                return {"status": "error", "message": f"Invalid alignment '{alignment}'. Use: left, center, right, justify"}
            para.alignment = align_map[alignment]
        for run in para.runs:
            if bold is not None:
                run.bold = bold
            if italic is not None:
                run.italic = italic
            if font_size:
                run.font.size = Inches(font_size / 72)
            if font_color:
                run.font.color.rgb = RGBColor.from_string(font_color)
        doc.save(path)
        return _save_and_return(path, "format_para", {"status": "ok", "index": index})
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def delete_para(path: str, index: int) -> dict:
    """Delete a paragraph.

    Args:
        path: Absolute path to the .docx file.
        index: Paragraph index (0-based).
    """
    try:
        path, err = _handle_docx(path)
        if err:
            return err
        doc = Document(path)
        if index < 0 or index >= len(doc.paragraphs):
            return {"status": "error", "message": f"Paragraph index {index} out of range (0-{len(doc.paragraphs)-1})"}
        para = doc.paragraphs[index]
        parent = para._element.getparent()
        parent.remove(para._element)
        doc.save(path)
        return _save_and_return(path, "delete_para", {"status": "ok", "index": index})
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def insert_table(path: str, rows: int, cols: int, data: list[list] | None = None, index: int | None = None) -> dict:
    """Insert a table.

    Args:
        path: Absolute path to the .docx file.
        rows: Number of rows.
        cols: Number of columns.
        data: Optional 2D array of cell values.
        index: Position (0-based) to insert at. None appends at end.
    """
    try:
        path, err = _handle_docx(path)
        if err:
            return err
        doc = _open_or_create_document(path)
        if data and (len(data) != rows or any(len(row) != cols for row in data)):
            return {"status": "error", "message": "Data dimensions don't match rows/cols"}
        table = doc.add_table(rows=rows, cols=cols)
        if data:
            for r_idx, row in enumerate(data):
                for c_idx, val in enumerate(row):
                    table.rows[r_idx].cells[c_idx].text = str(val) if val is not None else ""
        if index is not None and index < len(doc.tables) - 1:
            ref_table = doc.tables[index]
            ref_table._element.addprevious(table._element)
        doc.save(path)
        return _save_and_return(path, "insert_table", {"status": "ok", "rows": rows, "cols": cols, "index": index if index is not None else len(doc.tables) - 1})
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def modify_table(path: str, table_index: int, row: int, col: int, text: str) -> dict:
    """Modify a table cell.

    Args:
        path: Absolute path to the .docx file.
        table_index: Table index (0-based).
        row: Row index (0-based).
        col: Column index (0-based).
        text: New cell text.
    """
    try:
        path, err = _handle_docx(path)
        if err:
            return err
        doc = Document(path)
        if table_index < 0 or table_index >= len(doc.tables):
            return {"status": "error", "message": f"Table index {table_index} out of range (0-{len(doc.tables)-1})"}
        table = doc.tables[table_index]
        if row < 0 or row >= len(table.rows):
            return {"status": "error", "message": f"Row {row} out of range (0-{len(table.rows)-1})"}
        if col < 0 or col >= len(table.columns):
            return {"status": "error", "message": f"Column {col} out of range (0-{len(table.columns)-1})"}
        old_text = table.rows[row].cells[col].text
        table.rows[row].cells[col].text = text
        doc.save(path)
        return _save_and_return(path, "modify_table", {"status": "ok", "table_index": table_index, "row": row, "col": col, "old_text": old_text, "new_text": text})
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def format_table(path: str, table_index: int, style: str | None = None) -> dict:
    """Format a table.

    Args:
        path: Absolute path to the .docx file.
        table_index: Table index (0-based).
        style: Table style name (e.g. "Table Grid", "Light Shading").
    """
    try:
        path, err = _handle_docx(path)
        if err:
            return err
        doc = Document(path)
        if table_index < 0 or table_index >= len(doc.tables):
            return {"status": "error", "message": f"Table index {table_index} out of range (0-{len(doc.tables)-1})"}
        table = doc.tables[table_index]
        if style:
            try:
                table.style = doc.styles[style]
            except KeyError:
                return {"status": "error", "message": f"Style '{style}' not found"}
        doc.save(path)
        return _save_and_return(path, "format_table", {"status": "ok", "table_index": table_index, "style": style})
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def delete_table(path: str, table_index: int) -> dict:
    """Delete a table.

    Args:
        path: Absolute path to the .docx file.
        table_index: Table index (0-based).
    """
    try:
        path, err = _handle_docx(path)
        if err:
            return err
        doc = Document(path)
        if table_index < 0 or table_index >= len(doc.tables):
            return {"status": "error", "message": f"Table index {table_index} out of range (0-{len(doc.tables)-1})"}
        table = doc.tables[table_index]
        parent = table._element.getparent()
        parent.remove(table._element)
        doc.save(path)
        return _save_and_return(path, "delete_table", {"status": "ok", "table_index": table_index})
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def insert_image(path: str, image_path: str, index: int | None = None, width: float | None = None) -> dict:
    """Insert an image into the document.

    Args:
        path: Absolute path to the .docx file.
        image_path: Absolute path to the image file.
        index: Paragraph position (0-based) to insert at. None appends at end.
        width: Image width in inches. None uses original size.
    """
    try:
        path, err = _handle_docx(path)
        if err:
            return err
        doc = _open_or_create_document(path)
        if index is None or index >= len(doc.paragraphs):
            para = doc.add_paragraph()
        else:
            para = doc.add_paragraph()
            ref_para = doc.paragraphs[index]
            ref_para._element.addprevious(para._element)
        run = para.add_run()
        if width:
            run.add_picture(image_path, width=Inches(width))
        else:
            run.add_picture(image_path)
        doc.save(path)
        return _save_and_return(path, "insert_image", {"status": "ok", "image_path": image_path, "index": index})
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def delete_image(path: str, image_index: int) -> dict:
    """Delete an inline image by its occurrence index.

    Args:
        path: Absolute path to the .docx file.
        image_index: Image occurrence index (0-based, counting across all paragraphs).
    """
    try:
        path, err = _handle_docx(path)
        if err:
            return err
        doc = Document(path)
        current_index = 0
        for para in doc.paragraphs:
            for run in para.runs:
                drawings = run._element.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing")
                for drawing in drawings:
                    if current_index == image_index:
                        parent = drawing.getparent()
                        parent.remove(drawing)
                        doc.save(path)
                        return _save_and_return(path, "delete_image", {"status": "ok", "image_index": image_index})
                    current_index += 1
        return {"status": "error", "message": f"Image index {image_index} out of range (found {current_index} images)"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
