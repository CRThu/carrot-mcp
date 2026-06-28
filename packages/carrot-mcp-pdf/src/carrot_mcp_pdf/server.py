"""Carrot MCP PDF Server"""

import base64
import json
import os
import re
import sys
import tempfile
import threading
import time
from importlib.metadata import version as pkg_version

import pymupdf
import pymupdf4llm
from mcp.server.fastmcp import FastMCP

from carrot_mcp_pdf.cache import (
    load_cache,
    load_tasks,
    make_task_id,
    parse_page_range,
    save_cache,
    save_tasks,
)
from carrot_mcp_pdf.ocr import recognize_image

mcp = FastMCP("carrot-mcp-pdf")

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


def _resolve_multimodal(multimodal: bool) -> bool:
    """Resolve multimodal flag: CARROT_MCP_FORCE_MULTIMODAL overrides tool parameter if set."""
    if _MULTIMODAL_ENV is not None:
        return _MULTIMODAL_ENV.lower() == "true"
    return multimodal


def _vlm_configured() -> bool:
    """Check if VLM model and API key are configured for OCR."""
    return bool(VISION_MODEL and VISION_API_KEY)


def _read_image_as_base64(image_path: str) -> tuple[str, str]:
    """Read an image file and return (data_uri, mime_type) for embedding in markdown."""
    ext = os.path.splitext(image_path)[1].lower()
    mime = _MIME_MAP.get(ext, "image/jpeg")
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{b64}", mime


def _parse_page_content(text: str, image_dir: str, multimodal: bool) -> list[dict]:
    """Parse pymupdf4llm markdown output into ordered content blocks.

    Splits text by image references. Each image is either embedded as base64
    (multimodal=True) or sent to the vision model for OCR (multimodal=False).
    When VLM is not configured (no API key), falls back to base64 with a warning.
    data: URI images are skipped (already inline). Page numbers are 1-based.
    """
    multimodal = _resolve_multimodal(multimodal)
    blocks = []
    last_end = 0

    for match in _IMG_PATTERN.finditer(text):
        img_ref = match.group(1)

        text_before = text[last_end:match.start()].strip()
        if text_before:
            blocks.append({"type": "text", "data": text_before})

        last_end = match.end()

        if img_ref.startswith("data:"):
            continue

        img_path = os.path.join(image_dir, os.path.basename(img_ref))
        if os.path.exists(img_path):
            if multimodal:
                data_uri, mime = _read_image_as_base64(img_path)
                blocks.append({"type": "image", "base64": data_uri, "mime": mime})
            elif _vlm_configured():
                try:
                    ocr_result = recognize_image(
                        img_path,
                        model=VISION_MODEL,
                        api_key=VISION_API_KEY,
                        proxy=VISION_PROXY,
                    )
                except Exception:
                    ocr_result = "[Image recognition failed]"
                blocks.append({"type": "text", "data": ocr_result})
            else:
                data_uri, mime = _read_image_as_base64(img_path)
                blocks.append({"type": "image", "base64": data_uri, "mime": mime})
                blocks.append({"type": "text", "data": "[VLM model not configured, returning image as base64]"})

    remaining = text[last_end:].strip()
    if remaining:
        blocks.append({"type": "text", "data": remaining})

    return blocks


def _get_total_pages(pdf_path: str, cache: dict) -> int:
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


@mcp.tool()
def version() -> dict:
    """Get server version info and VLM configuration status.

    Returns:
        {status, name, version, vlm_model, vlm_configured}
    """
    return {
        "status": "ok",
        "name": "carrot-mcp-pdf",
        "version": pkg_version("carrot-mcp-pdf"),
        "vlm_model": VISION_MODEL,
        "vlm_configured": bool(VISION_MODEL and VISION_API_KEY),
    }


@mcp.tool()
def get_toc(pdf_path: str) -> dict:
    """Get table of contents from a PDF.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        {status, has_toc, total_pages, toc: [{level, title, start_page, end_page}]}
    """
    if not os.path.exists(pdf_path):
        return {"status": "error", "message": f"File not found: {pdf_path}"}

    try:
        doc = pymupdf.open(pdf_path)
        toc_raw = doc.get_toc()
        total_pages = doc.page_count
        doc.close()
    except Exception as e:
        return {"status": "error", "message": str(e)}

    cache = load_cache(pdf_path)
    cache["total_pages"] = total_pages

    if not toc_raw:
        save_cache(pdf_path, cache)
        return {
            "status": "ok",
            "has_toc": False,
            "total_pages": total_pages,
            "message": "No TOC found. This may be a scanned PDF. Use create_task for full conversion.",
        }

    toc_grouped = []
    for level, title, page in toc_raw:
        if toc_grouped and toc_grouped[-1]["level"] == level and toc_grouped[-1]["title"] == title:
            toc_grouped[-1]["end_page"] = page
        else:
            toc_grouped.append({
                "level": level,
                "title": title,
                "start_page": page,
                "end_page": page,
            })

    cache["toc"] = toc_grouped
    save_cache(pdf_path, cache)

    return {
        "status": "ok",
        "has_toc": True,
        "total_pages": total_pages,
        "toc": toc_grouped,
    }


@mcp.tool()
def get_pages(pdf_path: str, pages: str, multimodal: bool = True) -> dict:
    """Convert specific PDF pages to markdown.

    Args:
        pdf_path: Path to the PDF file.
        pages: Page range string, e.g. '1-5,8,10-12'.
        multimodal: If True, return images as base64 that you can analyze.
                    If False, send images to internal vlm for OCR and return contents of images.

    Returns:
        {status, pages: {page_num: {content: [{type, data/base64/mime}]}}, total_pages}
    """
    if not os.path.exists(pdf_path):
        return {"status": "error", "message": f"File not found: {pdf_path}"}

    try:
        page_list = parse_page_range(pages)
    except ValueError as e:
        return {"status": "error", "message": f"Invalid page range: {e}"}

    cache = load_cache(pdf_path)
    total_pages = _get_total_pages(pdf_path, cache)

    out_of_range = [p for p in page_list if p > total_pages]
    if out_of_range:
        return {
            "status": "error",
            "message": f"Pages out of range (total {total_pages}): {out_of_range}",
        }

    cached_pages = cache.get("pages", {})
    uncached = [p for p in page_list if str(p) not in cached_pages]

    if uncached:
        with tempfile.TemporaryDirectory() as tmp_dir:
            image_dir = os.path.join(tmp_dir, "images")
            os.makedirs(image_dir, exist_ok=True)

            try:
                page_chunks = pymupdf4llm.to_markdown(
                    pdf_path,
                    pages=[p - 1 for p in uncached],
                    write_images=True,
                    image_path=image_dir,
                    header=False,
                    footer=False,
                    use_ocr=False,
                )
            except Exception as e:
                return {"status": "error", "message": f"Conversion failed: {e}"}

            if isinstance(page_chunks, dict):
                page_chunks = [page_chunks]

            for i, chunk in enumerate(page_chunks):
                page_num = uncached[i] if i < len(uncached) else chunk.get("metadata", {}).get("page", i + 1)
                text = chunk.get("text", "")
                content = _parse_page_content(text, image_dir, multimodal)
                cached_pages[str(page_num)] = {"content": content}

        cache["pages"] = cached_pages
        save_cache(pdf_path, cache)

    result_pages = {}
    for p in page_list:
        page_data = cached_pages.get(str(p))
        if page_data:
            result_pages[str(p)] = page_data

    return {
        "status": "ok",
        "pages": result_pages,
        "total_pages": total_pages,
    }


def _convert_all(pdf_path: str, task_id: str, multimodal: bool):
    """Background thread: convert all pages of a PDF and update task progress.

    Runs in a daemon thread started by create_task. Each page is converted
    individually and cached to disk as it completes. Failed pages get empty content.
    """
    cache = load_cache(pdf_path)
    total_pages = _get_total_pages(pdf_path, cache)

    tasks = load_tasks(pdf_path)
    if task_id not in tasks:
        return

    cached_pages = cache.get("pages", {})

    with tempfile.TemporaryDirectory() as tmp_dir:
        image_dir = os.path.join(tmp_dir, "images")
        os.makedirs(image_dir, exist_ok=True)

        for page_num in range(1, total_pages + 1):
            if str(page_num) in cached_pages:
                tasks[task_id]["current_page"] = page_num
                tasks[task_id]["progress_percent"] = int(page_num / total_pages * 100)
                save_tasks(pdf_path, tasks)
                continue

            try:
                chunk = pymupdf4llm.to_markdown(
                    pdf_path,
                    pages=[page_num - 1],
                    write_images=True,
                    image_path=image_dir,
                    header=False,
                    footer=False,
                    use_ocr=False,
                )
                if isinstance(chunk, list):
                    chunk = chunk[0] if chunk else {}

                text = chunk.get("text", "")
                content = _parse_page_content(text, image_dir, multimodal)
                cached_pages[str(page_num)] = {"content": content}
            except Exception:
                cached_pages[str(page_num)] = {"content": [{"type": "text", "data": ""}]}

            cache["pages"] = cached_pages
            save_cache(pdf_path, cache)

            tasks[task_id]["current_page"] = page_num
            tasks[task_id]["progress_percent"] = int(page_num / total_pages * 100)
            save_tasks(pdf_path, tasks)

    tasks[task_id]["status"] = "completed"
    tasks[task_id]["progress_percent"] = 100
    save_tasks(pdf_path, tasks)


@mcp.tool()
def create_task(pdf_path: str, multimodal: bool = True) -> dict:
    """Start background full PDF conversion.

    Args:
        pdf_path: Path to the PDF file.
        multimodal: If True, include images as base64. If False, run OCR on images.

    Returns:
        {status, task_id, message, total_pages}
    """
    if not os.path.exists(pdf_path):
        return {"status": "error", "message": f"File not found: {pdf_path}"}

    cache = load_cache(pdf_path)
    total_pages = _get_total_pages(pdf_path, cache)

    task_id = make_task_id(pdf_path)
    tasks = load_tasks(pdf_path)
    tasks[task_id] = {
        "status": "running",
        "progress_percent": 0,
        "current_page": 0,
        "total_pages": total_pages,
        "multimodal": multimodal,
        "start_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    save_tasks(pdf_path, tasks)

    thread = threading.Thread(
        target=_convert_all, args=(pdf_path, task_id, multimodal), daemon=True
    )
    thread.start()

    return {
        "status": "ok",
        "task_id": task_id,
        "total_pages": total_pages,
        "message": "Background conversion started",
    }


def _find_task_in_files(task_id: str) -> dict | None:
    """Find a task by scanning task files. Uses task_id prefix for fast lookup."""
    import glob as glob_mod

    base = os.environ.get("APPDATA", os.path.expanduser("~/.local/share"))
    pattern = os.path.join(base, "carrot-mcp", "pdf", "*_tasks.json")

    for tasks_path in glob_mod.glob(pattern):
        try:
            with open(tasks_path, "r", encoding="utf-8") as f:
                tasks = json.load(f)
            if task_id in tasks:
                return tasks[task_id]
        except (json.JSONDecodeError, IOError):
            continue
    return None


@mcp.tool()
def get_status(task_id: str) -> dict:
    """Get status of a background conversion task.

    Args:
        task_id: The task ID returned by create_task.

    Returns:
        {status, task_id, conversion_status, progress_percent, current_page, total_pages}
    """
    task = _find_task_in_files(task_id)
    if task is None:
        return {"status": "error", "message": f"Task not found: {task_id}"}

    return {
        "status": "ok",
        "task_id": task_id,
        "conversion_status": task.get("status", "unknown"),
        "progress_percent": task.get("progress_percent", 0),
        "current_page": task.get("current_page", 0),
        "total_pages": task.get("total_pages", 0),
        "start_time": task.get("start_time", ""),
    }


def main():
    print("carrot-mcp-pdf server ready", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
