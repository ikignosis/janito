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
)
from janito.agent.runtime_config import unified_config
import pprint


class ConversationHandler:
    def __init__(self, client, model):
        self.client = client
        self.model = model
        self.usage_history = []

    def handle_conversation(
        self,
        messages,
        max_rounds=50,
        message_handler=None,
        verbose_response=False,
        spinner=False,
        max_tokens=None,
        verbose_events=False,
        stream=False,
        verbose_stream=False,
    ):
        if not messages:
            raise ValueError("No prompt provided in messages")

        resolved_max_tokens = max_tokens
        if resolved_max_tokens is None:
            resolved_max_tokens = unified_config.get("max_tokens", 200000)
        try:
            resolved_max_tokens = int(resolved_max_tokens)
        except (TypeError, ValueError):
            raise ValueError(
                f"max_tokens must be an integer, got: {resolved_max_tokens!r}"
            )

        for _ in range(max_rounds):
            if stream:
                # Streaming mode
                def get_stream():
                    return get_openai_stream_response(
                        self.client,
                        self.model,
                        messages,
                        resolved_max_tokens,
                        verbose_stream=verbose_stream,
                        message_handler=message_handler,
                    )

                retry_api_call(get_stream)
                return None
            else:
                # Non-streaming mode
                def api_call():
                    return get_openai_response(
                        self.client, self.model, messages, resolved_max_tokens
                    )

                if spinner:
                    response = show_spinner(
                        "Waiting for AI response...", retry_api_call, api_call
                    )
                else:
                    response = retry_api_call(api_call)
                    print("[DEBUG] OpenAI API raw response:", repr(response))

            if verbose_response:
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
            if verbose_events:
                print_verbose_event(event)
            if message_handler is not None and choice.message.content:
                message_handler.handle_message(event)
            if not choice.message.tool_calls:
                agent_idx = len([m for m in messages if m.get("role") == "agent"])
                self.usage_history.append(
                    {"agent_index": agent_idx, "usage": usage_info}
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
            agent_idx = len([m for m in messages if m.get("role") == "agent"])
            self.usage_history.append({"agent_index": agent_idx, "usage": usage_info})
            messages.append(
                {
                    "role": "assistant",
                    "content": choice.message.content,
                    "tool_calls": [tc.to_dict() for tc in choice.message.tool_calls],
                }
            )
            for tr in tool_responses:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tr["tool_call_id"],
                        "content": tr["content"],
                    }
                )
        raise MaxRoundsExceededError("Max conversation rounds exceeded")
