"""Multimodal image recognition via litellm."""

import base64
import os

import litellm

from carrot_mcp_pdf.cache import MIME_MAP

# OCR_PROMPT = "Extract all text from this image. Output only the raw text, no explanation. Preserve the original layout as closely as possible."
OCR_PROMPT = """
请识别并提取这张图片中的所有内容。按以下规则处理：

1. **文字内容**：逐行提取，保留原始排版结构（标题、段落、列表、表格等）
2. **表格**：转换为 Markdown 表格格式
3. **嵌入的图表/示意图/流程图**：
   - 用 `> [图]` 标记开始
   - **结构化转换**：尽量将图表内容转换为可读格式
     - 流程图/状态机 → Mermaid 语法
     - 对比/参数表 → Markdown 表格
     - 层级关系 → 列表缩进
   - **核心信息提取**：列出图中的关键要素、数值、标签
   - **推论分析**：基于图表内容给出合理推断，用 `[推断]` 标记
   - 用 `> [/图]` 标记结束
4. **无法识别的内容**：标记为 `[未识别]`

输出要求：
- 只输出识别到的内容，不要添加额外解释
- 保持原文的阅读顺序
- 如果是纯文字页面，直接输出文字即可
"""


def recognize_image(
    image_path: str,
    model: str | None = None,
    api_key: str | None = None,
    proxy: str | None = None,
    timeout: float = 60.0,
) -> str:
    """Send image to vision model for OCR/description.

    Args:
        image_path: Path to the image file.
        model: Vision model name (default: CARROT_MCP_MODEL env var).
        api_key: API key (default: CARROT_MCP_APIKEY env var).
        proxy: HTTP proxy URL (default: CARROT_MCP_PROXY env var).
        timeout: API call timeout in seconds.

    Returns:
        Text description of the image content.
    """

    model = model or os.environ.get("CARROT_MCP_MODEL")
    api_key = api_key or os.environ.get("CARROT_MCP_APIKEY")
    proxy = proxy or os.environ.get("CARROT_MCP_PROXY")

    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()

    ext = os.path.splitext(image_path)[1].lower()
    mime = MIME_MAP.get(ext, "image/jpeg")

    kwargs: dict = {"model": model, "timeout": timeout}
    if api_key:
        kwargs["api_key"] = api_key
    if proxy:
        kwargs["proxy"] = proxy

    response = litellm.completion(
        **kwargs,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": OCR_PROMPT,
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{image_b64}"},
                    },
                ],
            }
        ],
    )
    content = response.choices[0].message.content
    return content if content is not None else "[No response from vision model]"
