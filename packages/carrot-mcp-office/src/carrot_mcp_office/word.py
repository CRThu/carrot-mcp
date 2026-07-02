"""Word tools for carrot-mcp-office using python-docx."""

from __future__ import annotations

import base64
import json
import os

from docx import Document
from docx.shared import Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from mcp.types import ImageContent, TextContent

from carrot_mcp_office._mcp import mcp, _save_and_return
from carrot_mcp_office.convert import ensure_docx_format

_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_R_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


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
        ref_table = None
        if index is not None and index < len(doc.tables):
            ref_table = doc.tables[index]
        table = doc.add_table(rows=rows, cols=cols)
        if data:
            for r_idx, row in enumerate(data):
                for c_idx, val in enumerate(row):
                    table.rows[r_idx].cells[c_idx].text = str(val) if val is not None else ""
        if ref_table is not None:
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
            ref_para = doc.paragraphs[index]
            para = doc.add_paragraph()
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


def _heading_level(style_name: str) -> int | None:
    """Return heading level (1-9) from style name, or None if not a heading."""
    if style_name.startswith("Heading "):
        try:
            return int(style_name.split(" ", 1)[1])
        except (ValueError, IndexError):
            pass
    return None


def _flatten_outline(nodes: list[dict]) -> list[dict]:
    """Flatten outline tree into a list with parent tracking."""
    result = []
    for node in nodes:
        result.append({
            "level": node["level"],
            "title": node["title"],
            "index": node["index"],
            "parent": node.get("parent"),
        })
        if node.get("children"):
            result.extend(_flatten_outline(node["children"]))
    return result


def _has_images_in_para(para) -> bool:
    return bool(para._element.findall(f".//{_NS}drawing"))


def _extract_images_from_para(para) -> list[tuple[bytes, str]]:
    """Extract (image_bytes, mime_type) from a paragraph's inline drawings."""
    images = []
    for drawing in para._element.findall(f".//{_NS}drawing"):
        for blip in drawing.findall(f".//{_A_NS}blip"):
            rId = blip.get(f"{_R_NS}embed")
            if not rId:
                continue
            rel = para.part.rels.get(rId)
            if rel is None:
                continue
            img_part = rel.target_part
            img_bytes = img_part.blob
            content_type = img_part.content_type or "image/png"
            images.append((img_bytes, content_type))
    return images


def _parse_sections(raw: list, max_index: int) -> list[int]:
    """Parse section spec into flat list of 0-based indices.

    Accepts:
      - int: used directly (e.g. [0, 2])
      - str range: "0-9" expands to 0..9 (e.g. ["0-9"] → [0,1,...,9])
      - str mixed: "0-4,6,8" expands to [0,1,2,3,4,6,8]
      - str single: "3" treated as int 3
    """
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


@mcp.tool()
def get_outline(path: str) -> dict:
    """Get document outline (heading hierarchy).

    Returns a hierarchical tree of headings (Heading 1–9) with their
    paragraph indices. Use the returned indices with get_content_by_outline
    to fetch section content.

    Args:
        path: Absolute path to the .docx file.
    """
    try:
        doc = Document(path)
        headings = []
        for i, para in enumerate(doc.paragraphs):
            level = _heading_level(para.style.name)
            if level is not None:
                headings.append({"level": level, "title": para.text, "index": i})

        stack: list[dict] = []
        tree: list[dict] = []
        for h in headings:
            node = {"level": h["level"], "title": h["title"], "index": h["index"], "children": []}
            while stack and stack[-1]["level"] >= h["level"]:
                stack.pop()
            if stack:
                node["parent"] = stack[-1]["title"]
                stack[-1]["children"].append(node)
            else:
                tree.append(node)
            stack.append(node)

        flat = _flatten_outline(tree)
        return {
            "status": "ok",
            "path": path,
            "outline": tree,
            "flat": flat,
            "count": len(flat),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def get_content_by_outline(path: str, sections: list) -> list:
    """Get content for specific outline sections.

    Use get_outline first to obtain section indices, then pass them here
    to fetch paragraphs, tables, and images for each section.
    Images are returned as ImageContent attachments (not embedded in JSON).

    Args:
        path: Absolute path to the .docx file.
        sections: Indices to fetch. Supports:
            - int list: [0, 2, 5]
            - range string: ["0-9"] → 0,1,...,9
            - mixed: ["0-4", 6, 8] → 0,1,2,3,4,6,8

    Returns:
        list[TextContent | ImageContent] — first element is JSON metadata,
        followed by section content as TextContent and images as ImageContent.
    """
    try:
        doc = Document(path)
        flat = []
        for i, para in enumerate(doc.paragraphs):
            level = _heading_level(para.style.name)
            if level is not None:
                flat.append({"level": level, "title": para.text, "index": i})

        sec_indices = _parse_sections(sections, len(flat) - 1)
        result: list = []
        sections_meta = []

        for sec_idx in sec_indices:
            if sec_idx < 0 or sec_idx >= len(flat):
                sections_meta.append({"section": sec_idx, "error": f"Index out of range (0-{len(flat)-1})"})
                continue

            start = flat[sec_idx]["index"]
            end = len(doc.paragraphs)
            for k in range(sec_idx + 1, len(flat)):
                if flat[k]["level"] <= flat[sec_idx]["level"]:
                    end = flat[k]["index"]
                    break

            paragraphs = []
            tables = []
            img_idx = 0

            for j in range(start, end):
                para = doc.paragraphs[j]
                if para.text.strip():
                    paragraphs.append({"index": j, "text": para.text})
                for img_bytes, mime in _extract_images_from_para(para):
                    result.append(ImageContent(
                        type="image",
                        data=base64.b64encode(img_bytes).decode(),
                        mimeType=mime,
                        context=f"Section {sec_idx} ({flat[sec_idx]['title']}), image {img_idx}",
                    ))
                    img_idx += 1

            for t in doc.tables:
                t_elem = t._element
                t_index = None
                for k, child in enumerate(doc.element.body):
                    if child is t_elem:
                        t_index = k
                        break
                if t_index is not None and start <= t_index < end:
                    tables.append({
                        "rows": len(t.rows),
                        "cols": len(t.columns),
                        "data": [[cell.text for cell in row.cells] for row in t.rows],
                    })

            sections_meta.append({
                "section": sec_idx,
                "title": flat[sec_idx]["title"],
                "level": flat[sec_idx]["level"],
                "paragraph_range": [start, end - 1],
                "paragraphs": paragraphs,
                "tables": tables,
                "image_count": img_idx,
            })

        meta = {"status": "ok", "path": path, "sections": sections_meta, "count": len(sections_meta)}
        result.insert(0, TextContent(type="text", text=json.dumps(meta, ensure_ascii=False)))
        return result
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"status": "error", "message": str(e)}))]
