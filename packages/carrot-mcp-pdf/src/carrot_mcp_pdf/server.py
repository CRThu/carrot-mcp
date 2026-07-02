"""Carrot MCP PDF Server"""

import base64
import json
import os
import sys
import tempfile
import threading
import time
from importlib.metadata import version as pkg_version

import pymupdf
import pymupdf4llm
from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent, TextContent

from carrot_mcp_pdf.cache import (
    load_cache,
    load_tasks,
    make_task_id,
    parse_page_range,
    save_cache,
    save_tasks,
)
from carrot_mcp_pdf.converter import (
    VISION_API_KEY,
    VISION_MODEL,
    get_total_pages,
    ocr_page,
    parse_page_content,
)

mcp = FastMCP("carrot-mcp-pdf")


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
def get_pages(pdf_path: str, pages: str, multimodal: bool = True, force_ocr: bool = False) -> list:
    """Convert specific PDF pages to markdown.

    Args:
        pdf_path: Path to the PDF file.
        pages: Page range string, e.g. '1-5,8,10-12'.
        multimodal: If True, return images as attachments you can analyze.
                    If False, return OCR text of images.
        force_ocr: Render entire page as image and OCR it. Use when normal conversion
                   produces garbled text or missing content (e.g. scanned PDFs).
                   Sets PDF-level flag so future requests also use OCR.

    Returns:
        list[TextContent | ImageContent] — first element is JSON metadata (status, total_pages),
        followed by page content as TextContent blocks and images as ImageContent attachments.
    """
    if not os.path.exists(pdf_path):
        return [TextContent(type="text", text=json.dumps({"status": "error", "message": f"File not found: {pdf_path}"}))]

    try:
        page_list = parse_page_range(pages)
    except ValueError as e:
        return [TextContent(type="text", text=json.dumps({"status": "error", "message": f"Invalid page range: {e}"}))]

    cache = load_cache(pdf_path)
    total_pages = get_total_pages(pdf_path, cache)

    out_of_range = [p for p in page_list if p > total_pages]
    if out_of_range:
        return [TextContent(type="text", text=json.dumps({
            "status": "error",
            "message": f"Pages out of range (total {total_pages}): {out_of_range}",
        }))]

    if force_ocr:
        if not cache.get("force_ocr"):
            cache["pages"] = {}
        cache["force_ocr"] = True
        save_cache(pdf_path, cache)

    cached_pages = cache.get("pages", {})
    uncached = [p for p in page_list if str(p) not in cached_pages]
    failed_pages: list[int] = []

    if uncached:
        if force_ocr:
            failed_pages = []
            for page_num in uncached:
                try:
                    content = ocr_page(pdf_path, page_num)
                    cached_pages[str(page_num)] = {
                        "content": content,
                        "ocr_content": content,
                    }
                except Exception:
                    failed_pages.append(page_num)
        else:
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
                    return [TextContent(type="text", text=json.dumps({"status": "error", "message": f"Conversion failed: {e}"}))]

                if isinstance(page_chunks, str):
                    page_chunks = [{"text": page_chunks, "metadata": {}}]
                elif isinstance(page_chunks, dict):
                    page_chunks = [page_chunks]

                for i, chunk in enumerate(page_chunks):
                    page_num = uncached[i] if i < len(uncached) else chunk.get("metadata", {}).get("page", i + 1)
                    text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
                    content, ocr_content = parse_page_content(text, image_dir)
                    cached_pages[str(page_num)] = {
                        "content": content,
                        "ocr_content": ocr_content,
                    }

        cache["pages"] = cached_pages
        save_cache(pdf_path, cache)

    use_ocr = not multimodal or cache.get("force_ocr")
    meta = {
        "status": "ok",
        "total_pages": total_pages,
        "pages": [str(p) for p in page_list],
    }
    if failed_pages:
        meta["failed_pages"] = failed_pages
    result: list = [
        TextContent(type="text", text=json.dumps(meta)),
    ]

    for p in page_list:
        page_data = cached_pages.get(str(p))
        if not page_data:
            continue

        blocks = page_data["ocr_content"] if use_ocr and "ocr_content" in page_data else page_data["content"]
        result.append(TextContent(type="text", text=f"[Page {p}]"))
        img_idx = 0
        for block in blocks:
            if block["type"] == "text":
                result.append(TextContent(type="text", text=block["data"]))
            elif block["type"] == "image":
                img_bytes = block["data"]
                if isinstance(img_bytes, str):
                    img_bytes = base64.b64decode(img_bytes.split(",")[-1]) if "," in img_bytes else base64.b64decode(img_bytes)
                result.append(ImageContent(
                    type="image",
                    data=base64.b64encode(img_bytes).decode(),
                    mimeType=block.get("mime", "image/png"),
                    context=f"Page {p}, image {img_idx}",
                ))
                img_idx += 1

    return result


def _convert_all(pdf_path: str, task_id: str, multimodal: bool, force_ocr: bool = False):
    """Background thread: convert all pages of a PDF and update task progress.

    Runs in a daemon thread started by create_task. Each page is converted
    individually and cached to disk as it completes.
    - to_markdown (offline): fail immediately on error
    - ocr_page (API call): retry with exponential backoff (1s, 2s, 4s, 8s, 16s)
    On restart, skips already-cached pages (resume from last success).
    Completed tasks auto-delete from tasks.json; failed tasks retained for debugging.
    """
    import time as _time

    cache = load_cache(pdf_path)
    total_pages = get_total_pages(pdf_path, cache)

    if force_ocr:
        if not cache.get("force_ocr"):
            cache["pages"] = {}
        cache["force_ocr"] = True
        save_cache(pdf_path, cache)

    tasks = load_tasks(pdf_path)
    if task_id not in tasks:
        return

    cached_pages = cache.get("pages", {})
    MAX_OCR_RETRIES = 5

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
                if force_ocr:
                    content = None
                    for attempt in range(MAX_OCR_RETRIES):
                        try:
                            content = ocr_page(pdf_path, page_num)
                            break
                        except Exception as e:
                            import sys
                            wait = 2 ** attempt
                            print(f"[carrot-mcp-pdf] OCR page {page_num} attempt {attempt+1}/{MAX_OCR_RETRIES}: {e}", file=sys.stderr)
                            if attempt < MAX_OCR_RETRIES - 1:
                                print(f"[carrot-mcp-pdf] retrying in {wait}s...", file=sys.stderr)
                                _time.sleep(wait)
                            else:
                                raise
                    cached_pages[str(page_num)] = {
                        "content": content,
                        "ocr_content": content,
                    }
                else:
                    chunk = pymupdf4llm.to_markdown(
                        pdf_path,
                        pages=[page_num - 1],
                        write_images=True,
                        image_path=image_dir,
                        header=False,
                        footer=False,
                        use_ocr=False,
                    )
                    if isinstance(chunk, str):
                        chunk = {"text": chunk, "metadata": {}}
                    elif isinstance(chunk, list):
                        chunk = chunk[0] if chunk else {"text": "", "metadata": {}}
                    text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
                    content, ocr_content = parse_page_content(text, image_dir)
                    cached_pages[str(page_num)] = {
                        "content": content,
                        "ocr_content": ocr_content,
                    }

                cache["pages"] = cached_pages
                save_cache(pdf_path, cache)
            except Exception as e:
                import sys
                print(f"[carrot-mcp-pdf] page {page_num} failed, stopping: {e}", file=sys.stderr)
                # Break (not continue): OCR API network errors are likely persistent,
                # continuing would waste time retrying all subsequent pages.
                # On restart, cached pages are skipped so conversion resumes from here.
                tasks[task_id]["error_message"] = str(e)
                break

            tasks[task_id]["current_page"] = page_num
            tasks[task_id]["progress_percent"] = int(page_num / total_pages * 100)
            save_tasks(pdf_path, tasks)

    cached_count = len(cache.get("pages", {}))
    is_completed = cached_count == total_pages
    if is_completed:
        del tasks[task_id]
    else:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["progress_percent"] = int(cached_count / total_pages * 100) if total_pages > 0 else 0
        tasks[task_id]["cached_pages"] = cached_count
        tasks[task_id]["failed_at_page"] = cached_count + 1 if cached_count < total_pages else None
    save_tasks(pdf_path, tasks)


@mcp.tool()
def create_task(pdf_path: str, multimodal: bool = True, force_ocr: bool = False) -> dict:
    """Start background full PDF conversion.

    Args:
        pdf_path: Path to the PDF file.
        multimodal: If True, return images as MCP ImageContent attachments.
                    If False, run OCR on images and return text.
        force_ocr: Render entire page as image and OCR it. Use when normal conversion
                   produces garbled text or missing content (e.g. scanned PDFs).
                   Sets PDF-level flag so future requests also use OCR.

    Returns:
        {status, task_id, message, total_pages}
    """
    if not os.path.exists(pdf_path):
        return {"status": "error", "message": f"File not found: {pdf_path}"}

    cache = load_cache(pdf_path)
    total_pages = get_total_pages(pdf_path, cache)

    task_id = make_task_id(pdf_path)
    tasks = load_tasks(pdf_path)
    tasks[task_id] = {
        "status": "running",
        "progress_percent": 0,
        "current_page": 0,
        "total_pages": total_pages,
        "multimodal": multimodal,
        "force_ocr": force_ocr,
        "start_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    save_tasks(pdf_path, tasks)

    thread = threading.Thread(
        target=_convert_all, args=(pdf_path, task_id, multimodal, force_ocr), daemon=True
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
        {status, task_id, conversion_status, progress_percent, current_page, total_pages,
         cached_pages, failed_at_page, error_message, start_time}
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
        "cached_pages": task.get("cached_pages", 0),
        "failed_at_page": task.get("failed_at_page"),
        "error_message": task.get("error_message"),
        "start_time": task.get("start_time", ""),
    }


def main():
    print("carrot-mcp-pdf server ready", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
