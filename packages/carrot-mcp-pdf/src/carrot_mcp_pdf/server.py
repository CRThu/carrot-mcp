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
    get_total_pages,
    parse_page_content,
    read_image,
    render_page_as_image,
)

mcp = FastMCP("carrot-mcp-pdf")


@mcp.tool()
def version() -> dict:
    """Get server version info.

    Returns:
        {status, name, version}
    """
    return {
        "status": "ok",
        "name": "carrot-mcp-pdf",
        "version": pkg_version("carrot-mcp-pdf"),
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
def get_pages(pdf_path: str, pages: str | int | list | None, extract_text: bool = True) -> list:
    """Convert specific PDF pages to markdown or rendered images.

    Args:
        pdf_path: Path to the PDF file.
        pages: Page number(s) to convert. Accepts:
               - int: single page (e.g. 5 for page 5)
               - str: page range (e.g. '1-5,8,10-12')
               - list: array of int/str (e.g. [1, "3-5", 8])
               - None: returns empty list
        extract_text: If True, extract text content from PDF pages.
                      If False, render entire pages as images and return them.

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

    meta = {
        "status": "ok",
        "total_pages": total_pages,
        "pages": [str(p) for p in page_list],
    }
    result: list = [
        TextContent(type="text", text=json.dumps(meta)),
    ]

    if extract_text:
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
                    return [TextContent(type="text", text=json.dumps({"status": "error", "message": f"Conversion failed: {e}"}))]

                if isinstance(page_chunks, str):
                    page_chunks = [{"text": page_chunks, "metadata": {}}]
                elif isinstance(page_chunks, dict):
                    page_chunks = [page_chunks]

                for i, chunk in enumerate(page_chunks):
                    page_num = uncached[i] if i < len(uncached) else chunk.get("metadata", {}).get("page", i + 1)
                    text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
                    content = parse_page_content(text, image_dir)
                    cached_pages[str(page_num)] = {"content": content}

            cache["pages"] = cached_pages
            save_cache(pdf_path, cache)

        for p in page_list:
            page_data = cached_pages.get(str(p))
            if not page_data or "content" not in page_data:
                continue

            result.append(TextContent(type="text", text=f"[Page {p}]"))
            img_idx = 0
            for block in page_data["content"]:
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
    else:
        for p in page_list:
            try:
                image_path = render_page_as_image(pdf_path, p)
                img_bytes, mime = read_image(image_path)
                result.append(TextContent(type="text", text=f"[Page {p}]"))
                result.append(ImageContent(
                    type="image",
                    data=base64.b64encode(img_bytes).decode(),
                    mimeType=mime,
                    context=f"Page {p}",
                ))
                os.unlink(image_path)
            except Exception as e:
                result.append(TextContent(type="text", text=f"[Page {p}] Error: {e}"))

    return result


@mcp.tool()
def grep(pdf_path: str, pattern: str, regex: bool = False) -> dict:
    """Search for exact substring in PDF pages. NOT a semantic/fuzzy search.

    Uses pymupdf native text extraction — works on text-based PDFs only,
    not scanned/image-based PDFs. This is a literal text grep, not a
    natural language search engine. You must provide the exact text (or
    regex pattern) that appears in the document.

    Args:
        pdf_path: Path to the PDF file.
        pattern: Exact substring to match (case-insensitive). Use regex=True
                 for regular expression patterns.

    Returns:
        {status, pattern, total_pages, matches: [{page, index, text,
         context_before, context_after}], count}
    """
    if not os.path.exists(pdf_path):
        return {"status": "error", "message": f"File not found: {pdf_path}"}

    try:
        import re as re_mod
        doc = pymupdf.open(pdf_path)
        total_pages = doc.page_count

        if regex:
            regex_pattern = re_mod.compile(pattern, re_mod.IGNORECASE)
            def _match(text: str) -> bool:
                return bool(regex_pattern.search(text))
        else:
            def _match(text: str) -> bool:
                return pattern.lower() in text.lower()

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
            "pattern": pattern,
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
