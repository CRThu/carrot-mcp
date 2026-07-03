"""Carrot MCP PDF Server"""

import base64
import json
import os
import sys
import tempfile
from importlib.metadata import version as pkg_version

import pymupdf
import pymupdf4llm
from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent, TextContent

from carrot_mcp_pdf.cache import (
    load_cache,
    parse_page_range,
    save_cache,
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
            "message": "No TOC found. This may be a scanned PDF.",
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


@mcp.tool()
def search(pdf_path: str, query: str, regex: bool = False) -> dict:
    """Search for text in PDF pages (full-text search).

    Uses pymupdf native text extraction — works on text-based PDFs only,
    not scanned/image-based PDFs.

    Args:
        pdf_path: Path to the PDF file.
        query: Text to search for. Case-insensitive exact match by default,
               or regex if regex=True.

    Returns:
        {status, query, total_pages, matches: [{page, index, text,
         context_before, context_after}], count}
    """
    if not os.path.exists(pdf_path):
        return {"status": "error", "message": f"File not found: {pdf_path}"}

    try:
        import re as re_mod
        doc = pymupdf.open(pdf_path)
        total_pages = doc.page_count

        if regex:
            pattern = re_mod.compile(query, re_mod.IGNORECASE)
            def _match(text: str) -> bool:
                return bool(pattern.search(text))
        else:
            def _match(text: str) -> bool:
                return query.lower() in text.lower()

        matches = []
        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text("text")
            if not text.strip():
                continue

            lines = text.split("\n")
            for line_idx, line in enumerate(lines):
                if line.strip() and _match(line):
                    ctx_before = [lines[j].strip() for j in range(max(0, line_idx - 1), line_idx) if lines[j].strip()]
                    ctx_after = [lines[j].strip() for j in range(line_idx + 1, min(len(lines), line_idx + 2)) if lines[j].strip()]
                    matches.append({
                        "page": page_num + 1,
                        "index": line_idx,
                        "text": line.strip(),
                        "context_before": ctx_before,
                        "context_after": ctx_after,
                    })

        doc.close()
        return {
            "status": "ok",
            "pdf_path": pdf_path,
            "query": query,
            "regex": regex,
            "total_pages": total_pages,
            "matches": matches,
            "count": len(matches),
        }
    except re_mod.error as e:
        return {"status": "error", "message": f"Invalid regex: {e}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def main():
    print("carrot-mcp-pdf server ready", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
