"""PDF to markdown conversion with image processing."""

import base64
import os
import re
import tempfile

import pymupdf
import pymupdf4llm

from carrot_mcp_pdf.cache import MIME_MAP, save_cache

_IMG_PATTERN = re.compile(r"!\[.*?\]\((.*?)\)")


def read_image(image_path: str) -> tuple[bytes, str]:
    """Read an image file and return (raw_bytes, mime_type)."""
    ext = os.path.splitext(image_path)[1].lower()
    mime = MIME_MAP.get(ext, "image/jpeg")
    with open(image_path, "rb") as f:
        data = f.read()
    return data, mime


def render_page_as_image(pdf_path: str, page_num: int, dpi: int = 300) -> str:
    """Render a PDF page as a PNG image file. Returns path to the temp image."""
    doc = pymupdf.open(pdf_path)
    try:
        page = doc[page_num - 1]
        zoom = dpi / 72
        mat = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        fd, image_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        pix.save(image_path)
        return image_path
    finally:
        doc.close()


def parse_page_content(text: str, image_dir: str) -> list[dict]:
    """Parse pymupdf4llm markdown output into ordered content blocks.

    Returns list of content blocks:
    - Image blocks: {"type": "image", "data": base64_str, "mime": str}
    - Text blocks: {"type": "text", "data": str}

    data: URI images are skipped (already inline).
    """
    content = []
    last_end = 0

    for match in _IMG_PATTERN.finditer(text):
        img_ref = match.group(1)

        text_before = text[last_end:match.start()].strip()
        if text_before:
            content.append({"type": "text", "data": text_before})

        last_end = match.end()

        if img_ref.startswith("data:"):
            continue

        img_path = os.path.join(image_dir, os.path.basename(img_ref))
        if os.path.exists(img_path):
            img_bytes, mime = read_image(img_path)
            content.append({"type": "image", "data": base64.b64encode(img_bytes).decode(), "mime": mime})

    remaining = text[last_end:].strip()
    if remaining:
        content.append({"type": "text", "data": remaining})

    return content


def get_total_pages(pdf_path: str, cache: dict) -> int:
    """Get total page count from cache or by opening the PDF file.

    Updates cache with the result if it was not already cached.
    Returns 0 if the PDF cannot be opened (corrupted, inaccessible, etc.).
    """
    total = cache.get("total_pages", 0)
    if not total:
        try:
            doc = pymupdf.open(pdf_path)
            total = doc.page_count
            doc.close()
            cache["total_pages"] = total
            save_cache(pdf_path, cache)
        except Exception as e:
            import sys
            print(f"[carrot-mcp-pdf] cannot open PDF: {pdf_path}: {e}", file=sys.stderr)
    return total
