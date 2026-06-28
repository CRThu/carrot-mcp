"""PDF to markdown conversion with image processing."""

import base64
import os
import re
import tempfile

import pymupdf
import pymupdf4llm

from carrot_mcp_pdf.cache import save_cache
from carrot_mcp_pdf.ocr import recognize_image

_IMG_PATTERN = re.compile(r"!\[.*?\]\((.*?)\)")
_MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

VISION_MODEL = os.environ.get("CARROT_MCP_MODEL")
VISION_API_KEY = os.environ.get("CARROT_MCP_APIKEY")
VISION_PROXY = os.environ.get("CARROT_MCP_PROXY")
_MULTIMODAL_ENV = os.environ.get("CARROT_MCP_FORCE_MULTIMODAL")


def resolve_multimodal(multimodal: bool) -> bool:
    """Resolve multimodal flag: CARROT_MCP_FORCE_MULTIMODAL overrides tool parameter if set."""
    if _MULTIMODAL_ENV is not None:
        return _MULTIMODAL_ENV.lower() == "true"
    return multimodal


def vlm_configured() -> bool:
    """Check if VLM model and API key are configured for OCR."""
    return bool(VISION_MODEL and VISION_API_KEY)


def read_image_as_base64(image_path: str) -> tuple[str, str]:
    """Read an image file and return (data_uri, mime_type) for embedding in markdown."""
    ext = os.path.splitext(image_path)[1].lower()
    mime = _MIME_MAP.get(ext, "image/jpeg")
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{b64}", mime


def render_page_as_image(pdf_path: str, page_num: int, dpi: int = 300) -> str:
    """Render a PDF page as a PNG image file. Returns path to the temp image."""
    doc = pymupdf.open(pdf_path)
    page = doc[page_num - 1]
    zoom = dpi / 72
    mat = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    pix.save(tmp.name)
    doc.close()
    return tmp.name


def ocr_page(pdf_path: str, page_num: int) -> list[dict]:
    """Force OCR on a PDF page by rendering it as an image.

    Renders the entire page as a PNG image and sends it to the vision model for OCR.
    Returns a list containing a single text block with the OCR result.
    """
    if not vlm_configured():
        return [{"type": "text", "data": "[VLM model not configured, cannot force OCR]"}]

    image_path = render_page_as_image(pdf_path, page_num)
    try:
        ocr_result = recognize_image(
            image_path,
            model=VISION_MODEL,
            api_key=VISION_API_KEY,
            proxy=VISION_PROXY,
        )
        return [{"type": "text", "data": ocr_result}]
    except Exception as e:
        raise RuntimeError(f"OCR failed: {e}") from e
    finally:
        os.unlink(image_path)


def parse_page_content(text: str, image_dir: str) -> tuple[list[dict], list[dict]]:
    """Parse pymupdf4llm markdown output into ordered content blocks.

    Returns tuple of (content, ocr_content):
    - content: blocks with images as base64 (for multimodal=True)
    - ocr_content: blocks with images replaced by OCR text (for multimodal=False)

    data: URI images are skipped (already inline).
    """
    content = []
    ocr_content = []
    last_end = 0

    for match in _IMG_PATTERN.finditer(text):
        img_ref = match.group(1)

        text_before = text[last_end:match.start()].strip()
        if text_before:
            content.append({"type": "text", "data": text_before})
            ocr_content.append({"type": "text", "data": text_before})

        last_end = match.end()

        if img_ref.startswith("data:"):
            continue

        img_path = os.path.join(image_dir, os.path.basename(img_ref))
        if os.path.exists(img_path):
            data_uri, mime = read_image_as_base64(img_path)
            content.append({"type": "image", "base64": data_uri, "mime": mime})

            if vlm_configured():
                try:
                    ocr_result = recognize_image(
                        img_path,
                        model=VISION_MODEL,
                        api_key=VISION_API_KEY,
                        proxy=VISION_PROXY,
                    )
                except Exception as e:
                    raise RuntimeError(f"Image OCR failed: {e}") from e
                ocr_content.append({"type": "text", "data": ocr_result})
            else:
                ocr_content.append({"type": "image", "base64": data_uri, "mime": mime})
                ocr_content.append({"type": "text", "data": "[VLM model not configured, returning image as base64]"})

    remaining = text[last_end:].strip()
    if remaining:
        content.append({"type": "text", "data": remaining})
        ocr_content.append({"type": "text", "data": remaining})

    return content, ocr_content


def get_total_pages(pdf_path: str, cache: dict) -> int:
    """Get total page count from cache or by opening the PDF file.

    Updates cache with the result if it was not already cached.
    """
    total = cache.get("total_pages", 0)
    if not total:
        try:
            doc = pymupdf.open(pdf_path)
            total = doc.page_count
            doc.close()
            cache["total_pages"] = total
            save_cache(pdf_path, cache)
        except Exception:
            pass
    return total
