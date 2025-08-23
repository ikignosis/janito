import uuid
import traceback
import re
import json
import math
import time
import os
import logging
from rich import pretty
from janito.llm.driver import LLMDriver
from janito.llm.driver_input import DriverInput
from janito.driver_events import RequestFinished, RequestStatus, RateLimitRetry
from janito.llm.message_parts import TextMessagePart, FunctionCallMessagePart

import openai


class ZAIModelDriver(LLMDriver):
    # Check if required dependencies are available
    try:
        from zai import ZaiClient

        available = True
        unavailable_reason = None
    except ImportError as e:
        available = False
        unavailable_reason = f"Missing dependency: {str(e)}"

    def _get_message_from_result(self, result):
        """Extract the message object from the provider result (Z.AI-specific)."""
        if hasattr(result, "choices") and result.choices:
            return result.choices[0].message
        return None

    """
    Z.AI LLM driver (threaded, queue-based, stateless). Uses input/output queues accessible via instance attributes.
    """

    def __init__(self, tools_adapter=None, provider_name=None):
        super().__init__(tools_adapter=tools_adapter, provider_name=provider_name)

    def _prepare_api_kwargs(self, config, conversation):
        """
        Prepares API kwargs for Z.AI, including tool schemas if tools_adapter is present,
        and Z.AI-specific arguments (model, max_tokens, temperature, etc.).
        """
        api_kwargs = {}
        # Tool schemas (moved from base)
        if self.tools_adapter:
            try:
                from janito.providers.zai.schema_generator import (
                    generate_tool_schemas,
                )

                tool_classes = self.tools_adapter.get_tool_classes()
                tool_schemas = generate_tool_schemas(tool_classes)
                api_kwargs["tools"] = tool_schemas
            except Exception as e:
                api_kwargs["tools"] = []
                if hasattr(config, "verbose_api") and config.verbose_api:
                    print(f"[ZAIModelDriver] Tool schema generation failed: {e}")
        # Z.AI-specific parameters
        if config.model:
            api_kwargs["model"] = config.model
        # Use max_tokens for Z.ai SDK compatibility
        if hasattr(config, "max_tokens") and config.max_tokens is not None:
            api_kwargs["max_tokens"] = int(config.max_tokens)
        elif (
            hasattr(config, "max_completion_tokens")
            and config.max_completion_tokens is not None
        ):
            # Fallback to max_completion_tokens if max_tokens not set
            api_kwargs["max_tokens"] = int(config.max_completion_tokens)
        for p in (
            "temperature",
            "top_p",
            "presence_penalty",
            "frequency_penalty",
            "stop",
            "reasoning_effort",
        ):
            v = getattr(config, p, None)
            if v is not None:
                api_kwargs[p] = v
        api_kwargs["messages"] = conversation
        api_kwargs["stream"] = False
        # Always return the prepared kwargs, even if no tools are registered. The
        # OpenAI Python SDK expects a **mapping** – passing *None* will raise
        # ``TypeError: argument after ** must be a mapping, not NoneType``.
        return api_kwargs

    def _call_api(self, driver_input: DriverInput):
        """Call the Z.AI-compatible chat completion endpoint with retry and error handling."""
        cancel_event = getattr(driver_input, "cancel_event", None)
        config = driver_input.config
        conversation = self.convert_history_to_api_messages(
            driver_input.conversation_history
        )
        request_id = getattr(config, "request_id", None)
        self._print_api_call_start(config)
        client = self._instantiate_zai_client(config)
        api_kwargs = self._prepare_api_kwargs(config, conversation)
        max_retries = getattr(config, "max_retries", 3)
        attempt = 1
        while True:
            try:
                self._print_api_attempt(config, attempt, max_retries, api_kwargs)
                if self._check_cancel(cancel_event, request_id, before_call=True):
                    return None
                result = client.chat.completions.create(**api_kwargs)
                if self._check_cancel(cancel_event, request_id, before_call=False):
                    return None
                self._handle_api_success(config, result, request_id)
                return result
            except Exception as e:
                if self._handle_api_exception(
                    e, config, api_kwargs, attempt, max_retries, request_id
                ):
                    attempt += 1
                    continue
                raise

    def _print_api_call_start(self, config):
        if getattr(config, "verbose_api", False):
            tool_adapter_name = (
                type(self.tools_adapter).__name__ if self.tools_adapter else None
            )
            tool_names = []
            if self.tools_adapter and hasattr(self.tools_adapter, "list_tools"):
                try:
                    tool_names = self.tools_adapter.list_tools()
                except Exception:
                    tool_names = ["<error retrieving tools>"]
            print(
                f"[verbose-api] Z.AI API call about to be sent. Model: {config.model}, max_tokens: {config.max_tokens}, tools_adapter: {tool_adapter_name}, tool_names: {tool_names}",
                flush=True,
            )

    def _print_api_attempt(self, config, attempt, max_retries, api_kwargs):
        if getattr(config, "verbose_api", False):
            print(
                f"[Z.AI] API CALL (attempt {attempt}/{max_retries}): chat.completions.create(**{api_kwargs})",
                flush=True,
            )

    def _handle_api_success(self, config, result, request_id):
        self._print_verbose_result(config, result)
        usage_dict = self._extract_usage(result)
        if getattr(config, "verbose_api", False):
            print(
                f"[Z.AI][DEBUG] Attaching usage info to RequestFinished: {usage_dict}",
                flush=True,
            )
        self.output_queue.put(
            RequestFinished(
                driver_name=self.__class__.__name__,
                request_id=request_id,
                response=result,
                status=RequestStatus.SUCCESS,
                usage=usage_dict,
            )
        )
        if getattr(config, "verbose_api", False):
            pretty.install()
            print("[Z.AI] API RESPONSE:", flush=True)
            pretty.pprint(result)

    def _handle_api_exception(
        self, e, config, api_kwargs, attempt, max_retries, request_id
    ):
        status_code = getattr(e, "status_code", None)
        err_str = str(e)
        lower_err = err_str.lower()
        is_insufficient_quota = (
            "insufficient_quota" in lower_err
            or "exceeded your current quota" in lower_err
            or "exceeded_current_quota_error" in lower_err
        )
        is_rate_limit = (
            status_code == 429
            or "error code: 429" in lower_err
            or "resource_exhausted" in lower_err
        ) and not is_insufficient_quota
        if not is_rate_limit or attempt > max_retries:
            self._handle_fatal_exception(e, config, api_kwargs)
        retry_delay = self._extract_retry_delay_seconds(e)
        if retry_delay is None:
            retry_delay = min(2 ** (attempt - 1), 30)
        self.output_queue.put(
            RateLimitRetry(
                driver_name=self.__class__.__name__,
                request_id=request_id,
                attempt=attempt,
                retry_delay=retry_delay,
                error=err_str,
                details={},
            )
        )
        if getattr(config, "verbose_api", False):
            print(
                f"[Z.AI][RateLimit] Attempt {attempt}/{max_retries} failed with rate-limit. Waiting {retry_delay}s before retry.",
                flush=True,
            )
        start_wait = time.time()
        while time.time() - start_wait < retry_delay:
            if self._check_cancel(
                getattr(config, "cancel_event", None), request_id, before_call=False
            ):
                return False
            time.sleep(0.1)
        return True

    def _extract_retry_delay_seconds(self, exception) -> float | None:
        """Extract the retry delay in seconds from the provider error response.

        Handles both the Google Gemini style ``RetryInfo`` protobuf (where it's a
        ``retryDelay: '41s'`` string in JSON) and any number found after the word
        ``retryDelay``. Returns ``None`` if no delay could be parsed.
        """
        try:
            # Some SDKs expose the raw response JSON on e.args[0]
            if hasattr(exception, "response") and hasattr(exception.response, "text"):
                payload = exception.response.text
            else:
                payload = str(exception)
            # Look for 'retryDelay': '41s' or similar
            m = re.search(
                r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)(s)?", payload
            )
            if m:
                return float(m.group(1))
            # Fallback: generic number of seconds in the message
            m2 = re.search(r"(\d+(?:\.\d+)?)\s*s(?:econds)?", payload)
            if m2:
                return float(m2.group(1))
        except Exception:
            pass
        return None

    def _handle_fatal_exception(self, e, config, api_kwargs):
        """Common path for unrecoverable exceptions.

        Prints diagnostics (respecting ``verbose_api``) then re-raises the
        exception so standard error handling in ``LLMDriver`` continues.
        """
        is_verbose = getattr(config, "verbose_api", False)
        if is_verbose:
            print(f"[ERROR] Exception during Z.AI API call: {e}", flush=True)
            print(f"[ERROR] config: {config}", flush=True)
            print(
                f"[ERROR] api_kwargs: {api_kwargs if 'api_kwargs' in locals() else 'N/A'}",
                flush=True,
            )
            print("[ERROR] Full stack trace:", flush=True)
            print(traceback.format_exc(), flush=True)
        raise

    def _instantiate_zai_client(self, config):
        try:
            if not config.api_key:
                provider_name = getattr(self, "provider_name", "ZAI")
                from janito.llm.auth_utils import handle_missing_api_key

                handle_missing_api_key(
                    provider_name, f"{provider_name.upper()}_API_KEY"
                )

            api_key_display = str(config.api_key)
            if api_key_display and len(api_key_display) > 8:
                api_key_display = api_key_display[:4] + "..." + api_key_display[-4:]

            # HTTP debug wrapper
            if os.environ.get("ZAI_DEBUG_HTTP", "0") == "1":
                from http.client import HTTPConnection

                HTTPConnection.debuglevel = 1
                logging.basicConfig()
                logging.getLogger().setLevel(logging.DEBUG)
                requests_log = logging.getLogger("http.client")
                requests_log.setLevel(logging.DEBUG)
                requests_log.propagate = True
                print(
                    "[ZAIModelDriver] HTTP debug enabled via ZAI_DEBUG_HTTP=1",
                    flush=True,
                )

            # Use the official Z.ai SDK
            from zai import ZaiClient

            client = ZaiClient(
                api_key=config.api_key, base_url="https://api.z.ai/api/paas/v4/"
            )
            return client
        except Exception as e:
            print(
                f"[ERROR] Exception during Z.AI client instantiation: {e}", flush=True
            )
            print(traceback.format_exc(), flush=True)
            raise

    def _check_cancel(self, cancel_event, request_id, before_call=True):
        if cancel_event is not None and cancel_event.is_set():
            status = RequestStatus.CANCELLED
            reason = (
                "Cancelled before API call"
                if before_call
                else "Cancelled during API call"
            )
            self.output_queue.put(
                RequestFinished(
                    driver_name=self.__class__.__name__,
                    request_id=request_id,
                    status=status,
                    reason=reason,
                )
            )
            return True
        return False

    def _print_verbose_result(self, config, result):
        if config.verbose_api:
            print("[Z.AI] API RAW RESULT:", flush=True)
            pretty.pprint(result)
            if hasattr(result, "__dict__"):
                print("[Z.AI] API RESULT __dict__:", flush=True)
                pretty.pprint(result.__dict__)
            try:
                print("[Z.AI] API RESULT as dict:", dict(result), flush=True)
            except Exception:
                pass
            print(
                f"[Z.AI] API RESULT .usage: {getattr(result, 'usage', None)}",
                flush=True,
            )
            try:
                print(f"[Z.AI] API RESULT ['usage']: {result['usage']}", flush=True)
            except Exception:
                pass
            if not hasattr(result, "usage") or getattr(result, "usage", None) is None:
                print(
                    "[Z.AI][WARNING] No usage info found in API response.", flush=True
                )

    def _extract_usage(self, result):
        usage = getattr(result, "usage", None)
        if usage is not None:
            usage_dict = self._usage_to_dict(usage)
            if usage_dict is None:
                print(
                    "[Z.AI][WARNING] Could not convert usage to dict, using string fallback.",
                    flush=True,
                )
                usage_dict = str(usage)
        else:
            usage_dict = self._extract_usage_from_result_dict(result)
        return usage_dict

    def _usage_to_dict(self, usage):
        if hasattr(usage, "model_dump") and callable(getattr(usage, "model_dump")):
            try:
                return usage.model_dump()
            except Exception:
                pass
        if hasattr(usage, "dict") and callable(getattr(usage, "dict")):
            try:
                return usage.dict()
            except Exception:
                pass
        try:
            return dict(usage)
        except Exception:
            try:
                return vars(usage)
            except Exception:
                pass
        return None

    def _extract_usage_from_result_dict(self, result):
        try:
            return result["usage"]
        except Exception:
            return None

    def convert_history_to_api_messages(self, conversation_history):
        """
        Convert LLMConversationHistory to the list of dicts required by Z.AI's API.
        Handles 'tool_results' and 'tool_calls' roles for compliance.
        """
        api_messages = []
        for msg in conversation_history.get_history():
            self._append_api_message(api_messages, msg)
        self._replace_none_content(api_messages)
        return api_messages

    def _append_api_message(self, api_messages, msg):
        role = msg.get("role")
        content = msg.get("content")
        if role == "tool_results":
            self._handle_tool_results(api_messages, content)
        elif role == "tool_calls":
            self._handle_tool_calls(api_messages, content)
        else:
            self._handle_other_roles(api_messages, msg, role, content)

    def _handle_tool_results(self, api_messages, content):
        try:
            results = json.loads(content) if isinstance(content, str) else content
        except Exception:
            results = [content]
        for result in results:
            if isinstance(result, dict):
                api_messages.append(
                    {
                        "role": "tool",
                        "content": result.get("content", ""),
                        "name": result.get("name", ""),
                        "tool_call_id": result.get("tool_call_id", ""),
                    }
                )
            else:
                api_messages.append(
                    {
                        "role": "tool",
                        "content": str(result),
                        "name": "",
                        "tool_call_id": "",
                    }
                )

    def _handle_tool_calls(self, api_messages, content):
        try:
            tool_calls = json.loads(content) if isinstance(content, str) else content
        except Exception:
            tool_calls = []
        api_messages.append(
            {"role": "assistant", "content": "", "tool_calls": tool_calls}
        )

    def _handle_other_roles(self, api_messages, msg, role, content):
        if role == "function":
            name = ""
            if isinstance(msg, dict):
                metadata = msg.get("metadata", {})
                name = metadata.get("name", "") if isinstance(metadata, dict) else ""
            api_messages.append({"role": "tool", "content": content, "name": name})
        else:
            api_messages.append(msg)

    def _replace_none_content(self, api_messages):
        for m in api_messages:
            if m.get("content", None) is None:
                m["content"] = ""

    def _convert_completion_message_to_parts(self, message):
        """
        Convert a Z.AI completion message object to a list of MessagePart objects.
        Handles text, tool calls, and can be extended for other types.
        """
        parts = []
        # Text content
        content = getattr(message, "content", None)
        if content:
            parts.append(TextMessagePart(content=content))
        # Tool calls
        tool_calls = getattr(message, "tool_calls", None) or []
        for tool_call in tool_calls:
            parts.append(
                FunctionCallMessagePart(
                    tool_call_id=getattr(tool_call, "id", ""),
                    function=getattr(tool_call, "function", None),
                )
            )
        # Extend here for other message part types if needed
        return parts
