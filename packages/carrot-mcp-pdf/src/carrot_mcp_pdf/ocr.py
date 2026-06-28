"""Multimodal image recognition via litellm."""

import base64
import os


def recognize_image(
    image_path: str,
    model: str | None = None,
    api_key: str | None = None,
    proxy: str | None = None,
) -> str:
    """Send image to vision model for OCR/description.

    Args:
        image_path: Path to the image file.
        model: Vision model name (default: CARROT_MCP_MODEL env var or openai/gpt-4o).
        api_key: API key (default: CARROT_MCP_APIKEY env var).
        proxy: HTTP proxy URL (default: CARROT_MCP_PROXY env var).

    Returns:
        Text description of the image content.
    """
    import litellm

    model = model or os.environ.get("CARROT_MCP_MODEL", "openai/gpt-4o")
    api_key = api_key or os.environ.get("CARROT_MCP_APIKEY")
    proxy = proxy or os.environ.get("CARROT_MCP_PROXY")

    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()

    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}
    mime = mime_map.get(ext, "image/jpeg")

    kwargs = {"model": model}
    if api_key:
        kwargs["api_key"] = api_key
    if proxy:
        kwargs["api_base"] = proxy

    response = litellm.completion(
        **kwargs,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Describe this image in detail, including any text, diagrams, tables, or technical content. If it contains text, transcribe it exactly.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{image_b64}"},
                    },
                ],
            }
        ],
    )
    return response.choices[0].message.content
