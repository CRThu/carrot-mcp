"""Tests for Word tools."""

import base64
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
    insert_image,
    delete_image,
    get_outline,
    get_content_by_outline,
    _parse_sections,
)


def _parse_content_result(result):
    """Parse list[TextContent|ImageContent] return into (meta_dict, images_list)."""
    import json
    meta = json.loads(result[0].text)
    images = [r for r in result[1:] if r.type == "image"]
    return meta, images


def _cleanup(original_path):
    from carrot_mcp_office.backup import _mirror_path
    mirror = _mirror_path(original_path)
    if mirror.parent.exists():
        shutil.rmtree(mirror.parent, ignore_errors=True)
    d = os.path.dirname(original_path)
    if os.path.exists(d):
        shutil.rmtree(d, ignore_errors=True)


def _docx():
    d = tempfile.mkdtemp(prefix="test_office_")
    return os.path.join(d, "test.docx")


def _create_test_image():
    """Create a minimal 1x1 red PNG file for testing."""
    path = os.path.join(tempfile.gettempdir(), "test_office_img.png")
    # Minimal 1x1 red PNG
    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    )
    with open(path, "wb") as f:
        f.write(png_data)
    return path


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
        assert result["total_paragraphs"] >= 1
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
        assert info["total_paragraphs"] == 1
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


def test_insert_image():
    path = _docx()
    img_path = _create_test_image()
    try:
        result = insert_image(path, img_path)
        assert result["status"] == "ok"
        assert result["version"] >= 1
        info = word_inspect(path)
        assert info["image_count"] >= 1
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)
        if os.path.exists(img_path):
            os.unlink(img_path)


def test_insert_image_at_index():
    path = _docx()
    img_path = _create_test_image()
    try:
        insert_para(path, "First")
        insert_para(path, "Third")
        result = insert_image(path, img_path, index=1)
        assert result["status"] == "ok"
        info = word_inspect(path)
        assert info["paragraph_count"] == 3
        assert info["image_count"] == 1
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)
        if os.path.exists(img_path):
            os.unlink(img_path)


def test_insert_image_with_width():
    path = _docx()
    img_path = _create_test_image()
    try:
        result = insert_image(path, img_path, width=2.0)
        assert result["status"] == "ok"
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)
        if os.path.exists(img_path):
            os.unlink(img_path)


def test_delete_image():
    path = _docx()
    img_path = _create_test_image()
    try:
        insert_image(path, img_path)
        info = word_inspect(path)
        assert info["image_count"] == 1
        result = delete_image(path, 0)
        assert result["status"] == "ok"
        assert result["version"] >= 1
        info = word_inspect(path)
        assert info["image_count"] == 0
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)
        if os.path.exists(img_path):
            os.unlink(img_path)


def test_delete_image_out_of_range():
    path = _docx()
    try:
        insert_para(path, "Hello")
        result = delete_image(path, 0)
        assert result["status"] == "error"
        assert "out of range" in result["message"]
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_insert_table_at_index():
    path = _docx()
    try:
        insert_table(path, 2, 2, [["A", "B"], ["C", "D"]])
        insert_table(path, 1, 1, [["X"]], index=0)
        info = word_inspect(path)
        assert info["table_count"] == 2
        from docx import Document
        doc = Document(path)
        assert doc.tables[0].rows[0].cells[0].text == "X"
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_format_para_font_size_color():
    path = _docx()
    try:
        insert_para(path, "Hello")
        result = format_para(path, 0, font_size=14, font_color="FF0000")
        assert result["status"] == "ok"
        assert result["version"] >= 1
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def _create_heading_docx():
    """Create a test docx with heading hierarchy and content."""
    from docx import Document
    d = tempfile.mkdtemp(prefix="test_office_")
    path = os.path.join(d, "test.docx")
    doc = Document()
    doc.add_heading("Chapter 1", level=1)
    doc.add_paragraph("Intro text")
    doc.add_heading("Section 1.1", level=2)
    doc.add_paragraph("Section 1.1 content")
    doc.add_heading("Section 1.2", level=2)
    doc.add_paragraph("Section 1.2 content")
    doc.add_heading("Chapter 2", level=1)
    doc.add_paragraph("Chapter 2 content")
    doc.add_heading("Section 2.1", level=2)
    doc.add_paragraph("Section 2.1 content")
    doc.save(path)
    return path


def test_get_outline():
    path = _create_heading_docx()
    try:
        result = get_outline(path)
        assert result["status"] == "ok"
        assert result["count"] == 5
        assert len(result["outline"]) == 2
        assert result["outline"][0]["title"] == "Chapter 1"
        assert result["outline"][0]["level"] == 1
        assert len(result["outline"][0]["children"]) == 2
        assert result["outline"][1]["title"] == "Chapter 2"
        flat = result["flat"]
        assert flat[0]["title"] == "Chapter 1"
        assert flat[1]["title"] == "Section 1.1"
        assert flat[1]["parent"] == "Chapter 1"
        assert flat[3]["title"] == "Chapter 2"
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_get_outline_no_headings():
    path = _docx()
    try:
        insert_para(path, "Just text")
        result = get_outline(path)
        assert result["status"] == "ok"
        assert result["count"] == 0
        assert result["outline"] == []
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_get_content_by_outline():
    path = _create_heading_docx()
    try:
        result = get_content_by_outline(path, [0])
        meta, images = _parse_content_result(result)
        assert meta["status"] == "ok"
        assert meta["count"] == 1
        sec = meta["sections"][0]
        assert sec["title"] == "Chapter 1"
        assert sec["level"] == 1
        texts = [p["text"] for p in sec["paragraphs"]]
        assert "Intro text" in texts
        assert "Section 1.1 content" in texts
        assert "Section 1.2 content" in texts
        assert "Chapter 2 content" not in texts
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_get_content_by_outline_multiple():
    path = _create_heading_docx()
    try:
        result = get_content_by_outline(path, [1, 3])
        meta, _ = _parse_content_result(result)
        assert meta["status"] == "ok"
        assert meta["count"] == 2
        assert meta["sections"][0]["title"] == "Section 1.1"
        assert meta["sections"][1]["title"] == "Chapter 2"
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_get_content_by_outline_out_of_range():
    path = _create_heading_docx()
    try:
        result = get_content_by_outline(path, [99])
        meta, _ = _parse_content_result(result)
        assert meta["status"] == "ok"
        assert meta["sections"][0]["error"] is not None
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_get_content_by_outline_with_table():
    path = _create_heading_docx()
    try:
        insert_table(path, 2, 2, [["A", "B"], ["C", "D"]])
        result = get_content_by_outline(path, [0])
        meta, _ = _parse_content_result(result)
        assert meta["status"] == "ok"
        assert meta["count"] == 1
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_get_content_by_outline_empty_section():
    """Test getting content for a section that has no content paragraphs between headings."""
    from docx import Document
    d = tempfile.mkdtemp(prefix="test_office_")
    path = os.path.join(d, "test.docx")
    doc = Document()
    doc.add_heading("H1", level=1)
    doc.add_heading("H2", level=1)
    doc.add_heading("H3", level=1)
    doc.save(path)
    try:
        result = get_content_by_outline(path, [1])
        meta, _ = _parse_content_result(result)
        assert meta["status"] == "ok"
        sec = meta["sections"][0]
        assert sec["title"] == "H2"
        assert sec["paragraphs"] == [{"index": 1, "text": "H2"}]
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_get_outline_deep_nesting():
    """Test outline with 3+ levels of nesting."""
    from docx import Document
    d = tempfile.mkdtemp(prefix="test_office_")
    path = os.path.join(d, "test.docx")
    doc = Document()
    doc.add_heading("L1", level=1)
    doc.add_heading("L2", level=2)
    doc.add_heading("L3", level=3)
    doc.add_heading("L3b", level=3)
    doc.add_heading("L2b", level=2)
    doc.add_heading("L1b", level=1)
    doc.save(path)
    try:
        result = get_outline(path)
        assert result["status"] == "ok"
        assert result["count"] == 6
        tree = result["outline"]
        assert len(tree) == 2
        assert tree[0]["title"] == "L1"
        assert len(tree[0]["children"]) == 2
        assert tree[0]["children"][0]["title"] == "L2"
        assert len(tree[0]["children"][0]["children"]) == 2
        assert tree[0]["children"][1]["title"] == "L2b"
        flat = result["flat"]
        assert flat[2]["title"] == "L3"
        assert flat[2]["parent"] == "L2"
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_get_content_by_outline_last_section():
    """Test getting content for the last section (no next heading)."""
    from docx import Document
    d = tempfile.mkdtemp(prefix="test_office_")
    path = os.path.join(d, "test.docx")
    doc = Document()
    doc.add_heading("First", level=1)
    doc.add_paragraph("First content")
    doc.add_heading("Last", level=1)
    doc.add_paragraph("Last content A")
    doc.add_paragraph("Last content B")
    doc.save(path)
    try:
        result = get_content_by_outline(path, [1])
        meta, _ = _parse_content_result(result)
        assert meta["status"] == "ok"
        sec = meta["sections"][0]
        assert sec["title"] == "Last"
        texts = [p["text"] for p in sec["paragraphs"]]
        assert "Last content A" in texts
        assert "Last content B" in texts
        assert "First content" not in texts
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_get_outline_empty_heading_text():
    """Test outline with empty heading text."""
    from docx import Document
    d = tempfile.mkdtemp(prefix="test_office_")
    path = os.path.join(d, "test.docx")
    doc = Document()
    doc.add_heading("", level=1)
    doc.add_heading("Has Text", level=2)
    doc.add_heading("", level=1)
    doc.save(path)
    try:
        result = get_outline(path)
        assert result["status"] == "ok"
        assert result["count"] == 3
        assert result["flat"][0]["title"] == ""
        assert result["flat"][1]["title"] == "Has Text"
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_get_content_by_outline_with_images():
    """Test content retrieval returns images as ImageContent attachments."""
    img_path = _create_test_image()
    path = _create_heading_docx()
    try:
        insert_image(path, img_path, index=2)
        result = get_content_by_outline(path, [0])
        meta, images = _parse_content_result(result)
        assert meta["status"] == "ok"
        sec = meta["sections"][0]
        assert sec["image_count"] >= 1
        assert len(images) >= 1
        assert images[0].type == "image"
        assert images[0].data is not None
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)
        if os.path.exists(img_path):
            os.unlink(img_path)


def test_get_content_by_outline_range_string():
    """Test range string like '0-2' expands correctly."""
    path = _create_heading_docx()
    try:
        result = get_content_by_outline(path, ["0-2"])
        meta, _ = _parse_content_result(result)
        assert meta["status"] == "ok"
        assert meta["count"] == 3
        titles = [s["title"] for s in meta["sections"]]
        assert titles == ["Chapter 1", "Section 1.1", "Section 1.2"]
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_get_content_by_outline_mixed_spec():
    """Test mixed spec like ['0-1', 3] expands correctly."""
    path = _create_heading_docx()
    try:
        result = get_content_by_outline(path, ["0-1", 3])
        meta, _ = _parse_content_result(result)
        assert meta["status"] == "ok"
        assert meta["count"] == 3
        titles = [s["title"] for s in meta["sections"]]
        assert titles == ["Chapter 1", "Section 1.1", "Chapter 2"]
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_get_content_by_outline_string_index():
    """Test string index like '3' works the same as int 3."""
    path = _create_heading_docx()
    try:
        result = get_content_by_outline(path, ["3"])
        meta, _ = _parse_content_result(result)
        assert meta["status"] == "ok"
        assert meta["count"] == 1
        assert meta["sections"][0]["title"] == "Chapter 2"
    finally:
        _cleanup(path)
        if os.path.exists(path):
            os.unlink(path)


def test_parse_sections_ints():
    assert _parse_sections([0, 2, 5], 10) == [0, 2, 5]


def test_parse_sections_range():
    assert _parse_sections(["0-3"], 10) == [0, 1, 2, 3]


def test_parse_sections_mixed():
    assert _parse_sections(["0-2", 4, "6-8"], 10) == [0, 1, 2, 4, 6, 7, 8]


def test_parse_sections_dedup():
    assert _parse_sections([0, "0-1"], 10) == [0, 1]


def test_parse_sections_sorted():
    assert _parse_sections([5, "0-2"], 10) == [0, 1, 2, 5]


def test_parse_sections_string_int():
    assert _parse_sections(["3"], 10) == [3]


def test_parse_sections_negative():
    assert _parse_sections(["-1"], 10) == [-1]
