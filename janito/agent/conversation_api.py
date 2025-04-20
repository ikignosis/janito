"""
Handles OpenAI API calls and retry logic for conversation.
"""

import time
import json
from janito.agent.runtime_config import runtime_config
from janito.agent.tool_registry import get_tool_schemas


def get_openai_response(
    client, model, messages, max_tokens, tools=None, tool_choice=None, temperature=None
):
    """Non-streaming OpenAI API call."""
    if runtime_config.get("vanilla_mode", False):
        return client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )
    else:
        return client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools or get_tool_schemas(),
            tool_choice=tool_choice or "auto",
            temperature=temperature if temperature is not None else 0.2,
            max_tokens=max_tokens,
        )


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
                    f"Invalid/malformed response from OpenAI (attempt {attempt}/{max_retries}). Retrying in {wait_time} seconds..."
                )
                time.sleep(wait_time)
            else:
                print("Max retries for invalid response reached. Raising error.")
                raise last_exception
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                wait_time = 2**attempt
                print(
                    f"OpenAI API error (attempt {attempt}/{max_retries}): {e}. Retrying in {wait_time} seconds..."
                )
                time.sleep(wait_time)
            else:
                print("Max retries for OpenAI API error reached. Raising error.")
                raise last_exception
