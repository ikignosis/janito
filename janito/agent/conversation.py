from janito.agent.conversation_api import (
    get_openai_response,
    retry_api_call,
)
from janito.agent.conversation_tool_calls import handle_tool_calls
from janito.agent.conversation_ui import show_spinner, print_verbose_event
from janito.agent.conversation_exceptions import (
    MaxRoundsExceededError,
    EmptyResponseError,
    NoToolSupportError,
)
from janito.agent.runtime_config import unified_config, runtime_config
from janito.agent.api_exceptions import ApiError
import pprint


class ConversationHandler:
    def __init__(self, client, model):
        self.client = client
        self.model = model
        self.usage_history = []

    @staticmethod
    def remove_system_prompt(messages):
        """
        Return a new messages list with all system prompts removed.
        """
        return [msg for msg in messages if msg.get("role") != "system"]

    def _resolve_max_tokens(self, max_tokens):
        resolved_max_tokens = max_tokens
        if resolved_max_tokens is None:
            resolved_max_tokens = unified_config.get("max_tokens", 200000)
        try:
            resolved_max_tokens = int(resolved_max_tokens)
        except (TypeError, ValueError):
            raise ValueError(
                "max_tokens must be an integer, got: {resolved_max_tokens!r}".format(
                    resolved_max_tokens=resolved_max_tokens
                )
            )
        if runtime_config.get("vanilla_mode", False) and max_tokens is None:
            resolved_max_tokens = 8000
        return resolved_max_tokens

    def _call_openai_api(self, history, resolved_max_tokens, spinner):
        def api_call():
            return get_openai_response(
                self.client,
                self.model,
                history.get_messages(),
                resolved_max_tokens,
            )

        if spinner:
            response = show_spinner(
                "Waiting for AI response...", retry_api_call, api_call
            )
        else:
            response = retry_api_call(api_call)
        return response

    def _handle_no_tool_support(self, messages, max_tokens, spinner):
        print(
            "\u26a0\ufe0f Endpoint does not support tool use. Proceeding in vanilla mode (tools disabled)."
        )
        runtime_config.set("vanilla_mode", True)
        resolved_max_tokens = 8000
        if max_tokens is None:
            runtime_config.set("max_tokens", 8000)

        def api_call_vanilla():
            return get_openai_response(
                self.client, self.model, messages, resolved_max_tokens
            )

        if spinner:
            response = show_spinner(
                "Waiting for AI response (tools disabled)...",
                retry_api_call,
                api_call_vanilla,
            )
        else:
            response = retry_api_call(api_call_vanilla)
            print(
                "[DEBUG] OpenAI API raw response (tools disabled):",
                repr(response),
            )
        return response, resolved_max_tokens

    def _process_response(self, response):
        if runtime_config.get("verbose_response", False):
            pprint.pprint(response)
        if response is None or not getattr(response, "choices", None):
            error = getattr(response, "error", None)
            if error:
                print(f"ApiError: {error.get('message', error)}")
                raise ApiError(error.get("message", str(error)))
            raise EmptyResponseError(
                f"No choices in response; possible API or LLM error. Raw response: {response!r}"
            )
        choice = response.choices[0]
        usage = getattr(response, "usage", None)
        usage_info = (
            {
                "_debug_raw_usage": getattr(response, "usage", None),
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
            }
            if usage
            else None
        )
        return choice, usage_info

    def _handle_tool_calls(self, choice, history, message_handler, usage_info):
        tool_responses = handle_tool_calls(
            choice.message.tool_calls, message_handler=message_handler
        )
        agent_idx = len([m for m in history.get_messages() if m.get("role") == "agent"])
        self.usage_history.append({"agent_index": agent_idx, "usage": usage_info})
        history.add_message(
            {
                "role": "assistant",
                "content": choice.message.content,
                "tool_calls": [tc.to_dict() for tc in choice.message.tool_calls],
            }
        )
        for tool_response in tool_responses:
            history.add_message(
                {
                    "role": "tool",
                    "tool_call_id": tool_response["tool_call_id"],
                    "content": tool_response["content"],
                }
            )

    def handle_conversation(
        self,
        messages,
        max_rounds=100,
        message_handler=None,
        verbose_response=False,
        spinner=False,
        max_tokens=None,
        verbose_events=False,
    ):
        from janito.agent.conversation_history import ConversationHistory

        if isinstance(messages, ConversationHistory):
            history = messages
        else:
            history = ConversationHistory(messages)

        if len(history) == 0:
            raise ValueError("No prompt provided in messages")

        resolved_max_tokens = self._resolve_max_tokens(max_tokens)

        for _ in range(max_rounds):
            try:
                response = self._call_openai_api(history, resolved_max_tokens, spinner)
                error = getattr(response, "error", None)
                if error:
                    print(f"ApiError: {error.get('message', error)}")
                    raise ApiError(error.get("message", str(error)))
            except NoToolSupportError:
                response, resolved_max_tokens = self._handle_no_tool_support(
                    messages, max_tokens, spinner
                )
            choice, usage_info = self._process_response(response)
            event = {"type": "content", "message": choice.message.content}
            if runtime_config.get("verbose_events", False):
                print_verbose_event(event)
            if message_handler is not None and choice.message.content:
                message_handler.handle_message(event)
            if not choice.message.tool_calls:
                agent_idx = len(
                    [m for m in history.get_messages() if m.get("role") == "agent"]
                )
                self.usage_history.append(
                    {"agent_index": agent_idx, "usage": usage_info}
                )
                history.add_message(
                    {
                        "role": "assistant",
                        "content": choice.message.content,
                    }
                )
                return {
                    "content": choice.message.content,
                    "usage": usage_info,
                    "usage_history": self.usage_history,
                }
            self._handle_tool_calls(choice, history, message_handler, usage_info)
        raise MaxRoundsExceededError(f"Max conversation rounds exceeded ({max_rounds})")
