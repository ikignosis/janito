#!/usr/bin/env python3
"""
Create Image Tool - A class-based tool for generating images with the Wan
Image Generation model (``wan2.7-image-pro``).

The tool performs a text-to-image (T2I) request against the DashScope
multimodal-generation HTTP synchronous endpoint. The endpoint hostname is
derived from the configured **alibaba** provider endpoint (the per-provider
``endpoint`` override in ``config.json`` is honoured when present), keeping
the fixed ``/api/v1/services/aigc/multimodal-generation/generation`` path.

The generated PNG is downloaded and stored in a temporary file which is *not*
deleted, so it can be served back to the web frontend (which renders it as an
``<img>`` on a content card) and inspected by the user afterwards.

For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import json
import os
import tempfile
import time
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

from ...tooling import BaseTool
from ..decorator import tool

# Fixed DashScope multimodal-generation path appended to the provider host.
_GENERATION_PATH = "/api/v1/services/aigc/multimodal-generation/generation"

# The model used for image generation.
_MODEL = "wan2.7-image-pro"

# Valid output resolution specifications for text-to-image generation.
_VALID_SIZES = ("1K", "2K", "4K")

# Default output resolution.
_DEFAULT_SIZE = "2K"

# Environment variable fallback for the DashScope API key.
_DASHSCOPE_ENV_KEY = "DASHSCOPE_API_KEY"

# Generous timeout for image generation requests (seconds). Thinking mode
# enhances quality but increases generation time, so allow ample headroom.
_REQUEST_TIMEOUT = 300


def _alibaba_base_url() -> str | None:
    """Resolve the base URL for the ``alibaba`` provider.

    Prefers the per-provider ``endpoint`` override stored in ``config.json``
    (``alibaba.endpoint``) and falls back to the built-in provider default.

    Returns:
        The base URL string, or ``None`` when it cannot be determined.
    """
    try:
        from ...general_config import load_endpoint_from_config

        override = load_endpoint_from_config("alibaba")
        if override:
            return override
    except Exception:
        pass

    try:
        from ...provider_config import get_base_url_from_provider

        return get_base_url_from_provider("alibaba")
    except Exception:
        return None


def _generation_endpoint() -> str | None:
    """Build the full image-generation endpoint URL.

    Takes only the hostname (scheme + netloc) from the alibaba provider
    endpoint and appends the fixed DashScope generation path.
    """
    base = _alibaba_base_url()
    if not base:
        return None
    parsed = urlparse(base)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}{_GENERATION_PATH}"


def _resolve_api_key() -> str | None:
    """Resolve the DashScope API key.

    Order of precedence:
    1. The ``DASHSCOPE_API_KEY`` environment variable.
    2. The API key stored for the ``alibaba`` provider in the auth store.
    """
    env_key = os.getenv(_DASHSCOPE_ENV_KEY)
    if env_key:
        return env_key
    try:
        from ...auth_config import get_api_key

        return get_api_key("alibaba")
    except Exception:
        return None


@tool(permissions="w")
class CreateImage(BaseTool):
    """
    Generate an image from a text prompt using the Wan 2.7 Image Pro model.

    The generated image is saved to a temporary PNG file (which is kept, not
    deleted) and the path to that file is returned. When janito runs in
    ``--web`` mode, the frontend detects the ``CreateImage`` tool result and
    renders the image inline on a content card.

    Use this tool when the user wants to generate an image from a text
    description.

    Args:
        prompt (str): A text description of the image to generate.
        size (str): Output resolution — "1K", "2K" (default), or "4K".
    """

    @classmethod
    def should_load(cls) -> bool:
        """Only load when the active provider is alibaba and an endpoint is available."""
        try:
            from ...general_config import get_active_provider

            active = get_active_provider()
            if active.lower() != "alibaba":
                cls._load_skip_reason = (
                    f"Active provider is '{active}', not 'alibaba'; "
                    "CreateImage requires the alibaba provider"
                )
                return False
        except Exception:
            cls._load_skip_reason = "Could not determine the active provider"
            return False

        if _generation_endpoint() is None:
            cls._load_skip_reason = (
                "Could not resolve an 'alibaba' provider endpoint for image "
                "generation"
            )
            return False
        return True

    def run(self, prompt: str, size: str = _DEFAULT_SIZE) -> dict[str, Any]:
        """
        Generate an image from a text prompt and store it in a temp PNG file.

        Args:
            prompt (str): A text description of the image to generate.
            size (str): Output resolution — "1K", "2K" (default), or "4K".

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if the operation succeeded
                - 'image_path': path to the temporary PNG file (on success)
                - 'content_type': 'image' (hint for the frontend renderer)
                - 'prompt': the prompt that was used (echoed back)
                - 'usage': generation usage info (size/image_count/tokens)
                - 'request_id': the DashScope request id
                - 'error': error message (only present if success is False)
        """
        try:
            if not prompt or not prompt.strip():
                self.report_error("A non-empty 'prompt' is required")
                return {"success": False, "error": "A non-empty 'prompt' is required"}

            if not size:
                size = _DEFAULT_SIZE
            if size not in _VALID_SIZES:
                msg = (
                    f"Invalid size {size!r}; must be one of "
                    f"{', '.join(_VALID_SIZES)}"
                )
                self.report_error(msg)
                return {"success": False, "error": msg, "prompt": prompt}

            endpoint = _generation_endpoint()
            if not endpoint:
                self.report_error("No 'alibaba' provider endpoint configured")
                return {
                    "success": False,
                    "error": "No 'alibaba' provider endpoint configured",
                    "prompt": prompt,
                }

            api_key = _resolve_api_key()
            if not api_key:
                msg = (
                    f"No DashScope API key found. Set the {_DASHSCOPE_ENV_KEY} "
                    "environment variable or run: janito --set-api-key "
                    "--provider alibaba"
                )
                self.report_error(msg)
                return {"success": False, "error": msg, "prompt": prompt}

            self.report_start(f"🎨 Generating image with {_MODEL} ({size})", end="")

            payload = {
                "model": _MODEL,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"text": prompt}],
                        }
                    ]
                },
                "parameters": {
                    "size": size,
                    "n": 1,
                    "watermark": False,
                    "thinking_mode": True,
                },
            }

            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                method="POST",
            )
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", f"Bearer {api_key}")
            req.add_header("User-Agent", "Mozilla/5.0 (compatible; AI-Tool/1.0)")

            start_time = time.time()
            try:
                with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
            except urllib.error.HTTPError as e:
                detail = ""
                try:
                    detail = e.read().decode("utf-8", errors="replace")
                except Exception:
                    pass
                msg = f"HTTP Error {e.code}: {e.reason}"
                if detail:
                    msg += f" — {detail[:500]}"
                self.report_error(msg)
                return {"success": False, "error": msg, "prompt": prompt}
            except urllib.error.URLError as e:
                self.report_error(f"URL Error: {e.reason}")
                return {
                    "success": False,
                    "error": f"URL Error: {e.reason}",
                    "prompt": prompt,
                }

            try:
                data = json.loads(body)
            except json.JSONDecodeError as e:
                self.report_error(f"Invalid JSON response: {e}")
                return {
                    "success": False,
                    "error": f"Invalid JSON response: {e}",
                    "prompt": prompt,
                }

            # The API returns a top-level 'code'/'message' pair on failure.
            if data.get("code"):
                msg = f"{data.get('code')}: {data.get('message', 'unknown error')}"
                self.report_error(msg)
                return {
                    "success": False,
                    "error": msg,
                    "prompt": prompt,
                    "request_id": data.get("request_id"),
                }

            try:
                image_url = data["output"]["choices"][0]["message"]["content"][0][
                    "image"
                ]
            except (KeyError, IndexError, TypeError):
                self.report_error("Unexpected response structure (no image URL)")
                return {
                    "success": False,
                    "error": "Unexpected response structure (no image URL)",
                    "prompt": prompt,
                    "request_id": data.get("request_id"),
                }

            self.report_progress(" (downloading image)", end="")

            # Download the generated image into a temp file that is kept
            # (delete=False) so it can be served to the frontend / inspected.
            tmp = tempfile.NamedTemporaryFile(
                suffix=".png", prefix="janito_image_", delete=False
            )
            tmp_path = tmp.name
            tmp.close()
            try:
                img_req = urllib.request.Request(image_url)
                img_req.add_header(
                    "User-Agent", "Mozilla/5.0 (compatible; AI-Tool/1.0)"
                )
                with urllib.request.urlopen(
                    img_req, timeout=_REQUEST_TIMEOUT
                ) as img_resp:
                    with open(tmp_path, "wb") as fh:
                        while True:
                            chunk = img_resp.read(8192)
                            if not chunk:
                                break
                            fh.write(chunk)
            except Exception as e:
                # Best-effort cleanup of the empty/partial temp file.
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
                self.report_error(f"Failed to download generated image: {e}")
                return {
                    "success": False,
                    "error": f"Failed to download generated image: {e}",
                    "prompt": prompt,
                }

            execution_time_ms = int((time.time() - start_time) * 1000)
            size_bytes = os.path.getsize(tmp_path)
            self.report_result(f"Saved image to {tmp_path} ({size_bytes} bytes)")

            return {
                "success": True,
                "content_type": "image",
                "image_path": tmp_path,
                "prompt": prompt,
                "usage": data.get("usage"),
                "request_id": data.get("request_id"),
                "size_bytes": size_bytes,
                "execution_time_ms": execution_time_ms,
            }

        except Exception as e:
            self.report_error(f"Execution error: {e!s}")
            return {
                "success": False,
                "error": f"Failed to generate image: {e!s}",
                "prompt": prompt,
            }


# ── CLI testing harness ──────────────────────────────────────────────────────
def main():
    """Command line interface for testing the CreateImage tool."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate an image from a text prompt (Wan 2.7 Image Pro)"
    )
    parser.add_argument("prompt", help="Text description of the image to generate")
    parser.add_argument(
        "--size",
        default=_DEFAULT_SIZE,
        choices=_VALID_SIZES,
        help="Output resolution (default: %(default)s)",
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )
    args = parser.parse_args()

    result = CreateImage().run(prompt=args.prompt, size=args.size)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print("✅ Image generated")
            print(f"  File: {result['image_path']}")
            print(f"  Size: {result.get('size_bytes', 'N/A')} bytes")
            print(f"  Usage: {result.get('usage')}")
            print(f"  Request ID: {result.get('request_id')}")
        else:
            print(f"❌ Error: {result['error']}")

    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
