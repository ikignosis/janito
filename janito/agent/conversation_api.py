"""
Handles OpenAI API calls and retry logic for conversation.
"""

import time
from janito.i18n import tr
import json
from janito.agent.runtime_config import runtime_config
from janito.agent.tool_registry import get_tool_schemas
from janito.agent.conversation_exceptions import NoToolSupportError
from janito.agent.api_exceptions import ApiError


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
    """OpenAI API call."""
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
        # Always check for error before raising ProviderError
        error = getattr(response, "error", None)
        if error:
            print(f"ApiError: {error.get('message', error)}")
            print(f"Full error object: {error}")
            print(f"Raw response: {response}")
            raise ApiError(error.get("message", str(error)))
        raise ProviderError(
            f"No choices in response; possible API or LLM error. Raw response: {response!r}",
            {"code": 502, "raw_response": str(response)},
        )
    return response


def _extract_status_and_retry_after(e, error_message):
    status_code = None
    retry_after = None
    if hasattr(e, "status_code"):
        status_code = getattr(e, "status_code")
    elif hasattr(e, "response") and hasattr(e.response, "status_code"):
        status_code = getattr(e.response, "status_code")
        if hasattr(e.response, "headers") and e.response.headers:
            retry_after = e.response.headers.get("Retry-After")
    else:
        import re

        match = re.search(r"[Ee]rror code: (\d{3})", error_message)
        if match:
            status_code = int(match.group(1))
        retry_after_match = re.search(r"Retry-After['\"]?:?\s*(\d+)", error_message)
        if retry_after_match:
            retry_after = retry_after_match.group(1)
    return status_code, retry_after


def _calculate_wait_time(status_code, retry_after, attempt):
    if status_code == 429 and retry_after is not None:
        try:
            return int(float(retry_after))
        except Exception:
            return 2**attempt
    return 2**attempt


def _log_and_sleep(message, attempt, max_retries, e=None, wait_time=None):
    print(
        tr(
            message,
            attempt=attempt,
            max_retries=max_retries,
            e=e,
            wait_time=wait_time,
        )
    )
    time.sleep(wait_time)


def _handle_json_decode_error(e, attempt, max_retries):
    if attempt < max_retries:
        wait_time = 2**attempt
        _log_and_sleep(
            "Invalid/malformed response from OpenAI (attempt {attempt}/{max_retries}). Retrying in {wait_time} seconds...",
            attempt,
            max_retries,
            wait_time=wait_time,
        )
        return None
    else:
        print(tr("Max retries for invalid response reached. Raising error."))
        raise e


def _handle_general_exception(e, attempt, max_retries):
    error_message = str(e)
    if "No endpoints found that support tool use" in error_message:
        print(tr("API does not support tool use."))
        raise NoToolSupportError(error_message)
    status_code, retry_after = _extract_status_and_retry_after(e, error_message)
    if status_code is not None:
        if status_code == 429:
            wait_time = _calculate_wait_time(status_code, retry_after, attempt)
            if attempt < max_retries:
                _log_and_sleep(
                    "OpenAI API rate limit (429) (attempt {attempt}/{max_retries}): {e}. Retrying in {wait_time} seconds...",
                    attempt,
                    max_retries,
                    e=e,
                    wait_time=wait_time,
                )
                return None
            else:
                print("Max retries for OpenAI API rate limit reached. Raising error.")
                raise e
        elif 500 <= status_code < 600:
            wait_time = 2**attempt
            if attempt < max_retries:
                _log_and_sleep(
                    "OpenAI API server error (attempt {attempt}/{max_retries}): {e}. Retrying in {wait_time} seconds...",
                    attempt,
                    max_retries,
                    e=e,
                    wait_time=wait_time,
                )
                return None
            else:
                print("Max retries for OpenAI API server error reached. Raising error.")
                raise e
        elif 400 <= status_code < 500:
            print(
                tr(
                    "OpenAI API client error {status_code}: {e}. Not retrying.",
                    status_code=status_code,
                    e=e,
                )
            )
            raise e
    if attempt < max_retries:
        wait_time = 2**attempt
        _log_and_sleep(
            "OpenAI API error (attempt {attempt}/{max_retries}): {e}. Retrying in {wait_time} seconds...",
            attempt,
            max_retries,
            e=e,
            wait_time=wait_time,
        )
        return None
    else:
        print(tr("Max retries for OpenAI API error reached. Raising error."))
        raise e


def retry_api_call(api_func, max_retries=5, *args, **kwargs):
    for attempt in range(1, max_retries + 1):
        try:
            response = api_func(*args, **kwargs)
            error = getattr(response, "error", None)
            if error:
                print(f"ApiError: {error.get('message', error)}")
                raise ApiError(error.get("message", str(error)))
            return response
        except ApiError:
            raise
        except json.JSONDecodeError as e:
            result = _handle_json_decode_error(e, attempt, max_retries)
            if result is not None:
                return result
        except Exception as e:
            result = _handle_general_exception(e, attempt, max_retries)
            if result is not None:
                return result
