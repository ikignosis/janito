"""
Handles OpenAI API calls and retry logic for conversation.
"""

import time
from janito.i18n import tr
import json
from janito.agent.runtime_config import runtime_config
from janito.agent.tool_registry import get_tool_schemas
from janito.agent.conversation_exceptions import NoToolSupportError


def _sanitize_utf8_surrogates(obj):
    """
    Recursively sanitize a dict/list/string by replacing surrogate codepoints with the unicode replacement character.
    """
    if isinstance(obj, str):
        # Encode with surrogatepass, then decode with 'utf-8', replacing errors
        return obj.encode("utf-8", "replace").decode("utf-8", "replace")
    elif isinstance(obj, dict):
        return {k: _sanitize_utf8_surrogates(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_utf8_surrogates(x) for x in obj]
    else:
        return obj


def get_openai_response(
    client, model, messages, max_tokens, tools=None, tool_choice=None, temperature=None
):
    """Non-streaming OpenAI API call."""
    messages = _sanitize_utf8_surrogates(messages)
    from janito.agent.conversation_exceptions import ProviderError

    if runtime_config.get("vanilla_mode", False):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )
    else:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools or get_tool_schemas(),
            tool_choice=tool_choice or "auto",
            temperature=temperature if temperature is not None else 0.2,
            max_tokens=max_tokens,
        )
    # Explicitly check for missing or empty choices (API/LLM error)
    if (
        not hasattr(response, "choices")
        or response.choices is None
        or len(response.choices) == 0
    ):
        raise ProviderError(
            "No choices in response; possible API or LLM error.",
            {"code": 502, "raw_response": str(response)},
        )
    return response


def get_openai_stream_response(
    client,
    model,
    messages,
    max_tokens,
    tools=None,
    tool_choice=None,
    temperature=None,
    verbose_stream=False,
    message_handler=None,
):
    """Streaming OpenAI API call."""
    messages = _sanitize_utf8_surrogates(messages)
    openai_args = dict(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        stream=True,
    )
    if not runtime_config.get("vanilla_mode", False):
        openai_args.update(
            tools=tools or get_tool_schemas(),
            tool_choice=tool_choice or "auto",
            temperature=temperature if temperature is not None else 0.2,
        )
    response_stream = client.chat.completions.create(**openai_args)
    content_accum = ""
    for event in response_stream:
        if verbose_stream or runtime_config.get("verbose_stream", False):
            print(repr(event), flush=True)
        delta = getattr(event.choices[0], "delta", None)
        if delta and getattr(delta, "content", None):
            chunk = delta.content
            content_accum += chunk
            if message_handler:
                message_handler.handle_message({"type": "stream", "content": chunk})
    if message_handler:
        message_handler.handle_message({"type": "stream_end", "content": content_accum})
    return None


def retry_api_call(api_func, max_retries=5, *args, **kwargs):
    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            return api_func(*args, **kwargs)
        except json.JSONDecodeError as e:
            last_exception = e
            if attempt < max_retries:
                wait_time = 2**attempt
                print(
                    tr(
                        "Invalid/malformed response from OpenAI (attempt {attempt}/{max_retries}). Retrying in {wait_time} seconds...",
                        attempt=attempt,
                        max_retries=max_retries,
                        wait_time=wait_time,
                    )
                )
                time.sleep(wait_time)
            else:
                print(tr("Max retries for invalid response reached. Raising error."))
                raise last_exception
        except Exception as e:
            last_exception = e
            status_code = None
            error_message = str(e)
            retry_after = None
            # Detect specific tool support error
            if "No endpoints found that support tool use" in error_message:
                print(tr("API does not support tool use."))
                raise NoToolSupportError(error_message)
            # Try to extract status code and Retry-After from known exception types or message
            if hasattr(e, "status_code"):
                status_code = getattr(e, "status_code")
            elif hasattr(e, "response") and hasattr(e.response, "status_code"):
                status_code = getattr(e.response, "status_code")
                # Check for Retry-After header
                if hasattr(e.response, "headers") and e.response.headers:
                    retry_after = e.response.headers.get("Retry-After")
            else:
                # Try to parse from error message
                import re

                match = re.search(r"[Ee]rror code: (\d{3})", error_message)
                if match:
                    status_code = int(match.group(1))
                # Try to find Retry-After in message
                retry_after_match = re.search(
                    r"Retry-After['\"]?:?\s*(\d+)", error_message
                )
                if retry_after_match:
                    retry_after = retry_after_match.group(1)
            # Decide retry logic based on status code
            if status_code is not None:
                if status_code == 429:
                    # Use Retry-After if available, else exponential backoff
                    if retry_after is not None:
                        try:
                            wait_time = int(float(retry_after))
                        except Exception:
                            wait_time = 2**attempt
                    else:
                        wait_time = 2**attempt
                    if attempt < max_retries:
                        print(
                            tr(
                                "OpenAI API rate limit (429) (attempt {attempt}/{max_retries}): {e}. Retrying in {wait_time} seconds...",
                                attempt=attempt,
                                max_retries=max_retries,
                                e=e,
                                wait_time=wait_time,
                            )
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        print(
                            "Max retries for OpenAI API rate limit reached. Raising error."
                        )
                        raise last_exception
                elif 500 <= status_code < 600:
                    # Retry on server errors
                    if attempt < max_retries:
                        wait_time = 2**attempt
                        print(
                            tr(
                                "OpenAI API server error (attempt {attempt}/{max_retries}): {e}. Retrying in {wait_time} seconds...",
                                attempt=attempt,
                                max_retries=max_retries,
                                e=e,
                                wait_time=wait_time,
                            )
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        print(
                            "Max retries for OpenAI API server error reached. Raising error."
                        )
                        raise last_exception
                elif 400 <= status_code < 500:
                    # Do not retry on client errors (except 429)
                    print(
                        tr(
                            "OpenAI API client error {status_code}: {e}. Not retrying.",
                            status_code=status_code,
                            e=e,
                        )
                    )
                    raise last_exception
            # If status code not detected, fallback to previous behavior
            if attempt < max_retries:
                wait_time = 2**attempt
                print(
                    tr(
                        "OpenAI API error (attempt {attempt}/{max_retries}): {e}. Retrying in {wait_time} seconds...",
                        attempt=attempt,
                        max_retries=max_retries,
                        e=e,
                        wait_time=wait_time,
                    )
                )
                time.sleep(wait_time)
            else:
                print(tr("Max retries for OpenAI API error reached. Raising error."))
                raise last_exception
