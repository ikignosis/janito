from janito.agent.conversation_api import (
    get_openai_response,
    get_openai_stream_response,
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

    def handle_conversation(
        self,
        messages,
        max_rounds=100,
        message_handler=None,
        verbose_response=False,
        spinner=False,
        max_tokens=None,
        verbose_events=False,
        stream=False,
        verbose_stream=False,
    ):
        from janito.agent.conversation_history import ConversationHistory

        # Accept either ConversationHistory or a list for backward compatibility
        if isinstance(messages, ConversationHistory):
            history = messages
        else:
            history = ConversationHistory(messages)

        if len(history) == 0:
            raise ValueError("No prompt provided in messages")

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

        # If vanilla mode is set and max_tokens was not provided, default to 8000
        if runtime_config.get("vanilla_mode", False) and max_tokens is None:
            resolved_max_tokens = 8000

        for _ in range(max_rounds):
            try:
                if stream:
                    # Streaming mode
                    def get_stream():
                        return get_openai_stream_response(
                            self.client,
                            self.model,
                            history.get_messages(),
                            resolved_max_tokens,
                            verbose_stream=runtime_config.get("verbose_stream", False),
                            message_handler=message_handler,
                        )

                    retry_api_call(get_stream)
                    return None
                else:
                    # Non-streaming mode
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
            except NoToolSupportError:
                print(
                    "⚠️ Endpoint does not support tool use. Proceeding in vanilla mode (tools disabled)."
                )
                runtime_config.set("vanilla_mode", True)
                if max_tokens is None:
                    runtime_config.set("max_tokens", 8000)
                    resolved_max_tokens = 8000

                # Remove system prompt for vanilla mode if needed (call this externally when appropriate)
                # messages = ConversationHandler.remove_system_prompt(messages)
                # Retry once with tools disabled
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
            if runtime_config.get("verbose_response", False):
                pprint.pprint(response)
            if response is None or not getattr(response, "choices", None):
                raise EmptyResponseError(
                    f"No choices in response; possible API or LLM error. Raw response: {response!r}"
                )
            choice = response.choices[0]
            usage = getattr(response, "usage", None)
            usage_info = (
                {
                    # DEBUG: Show usage extraction
                    "_debug_raw_usage": getattr(response, "usage", None),
                    "prompt_tokens": getattr(usage, "prompt_tokens", None),
                    "completion_tokens": getattr(usage, "completion_tokens", None),
                    "total_tokens": getattr(usage, "total_tokens", None),
                }
                if usage
                else None
            )
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
                # Add assistant response to history
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
            # Tool calls
            tool_responses = handle_tool_calls(
                choice.message.tool_calls, message_handler=message_handler
            )
            agent_idx = len(
                [m for m in history.get_messages() if m.get("role") == "agent"]
            )
            self.usage_history.append({"agent_index": agent_idx, "usage": usage_info})
            # Add assistant response with tool calls
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
        raise MaxRoundsExceededError(f"Max conversation rounds exceeded ({max_rounds})")
