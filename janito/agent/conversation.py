import json
from janito.agent.tool_registry import get_tool_schemas, handle_tool_call
from janito.agent.runtime_config import runtime_config, unified_config
from rich.console import Console
import pprint

class MaxRoundsExceededError(Exception):
    pass

class EmptyResponseError(Exception):
    pass

class ProviderError(Exception):
    def __init__(self, message, error_data):
        self.error_data = error_data
        super().__init__(message)

class ConversationHandler:
    def __init__(self, client, model):
        self.client = client
        self.model = model
        self.usage_history = []

    def handle_conversation(self, messages, max_rounds=50, message_handler=None, verbose_response=False, spinner=False, max_tokens=None):
        max_tools = runtime_config.get('max_tools', None)
        tool_calls_made = 0
        if not messages:
            raise ValueError("No prompt provided in messages")

        # Resolve max_tokens priority: runtime param > config > default
        resolved_max_tokens = max_tokens
        if resolved_max_tokens is None:
            resolved_max_tokens = unified_config.get('max_tokens', 200000)

        # Ensure max_tokens is always an int (handles config/CLI string values)
        try:
            resolved_max_tokens = int(resolved_max_tokens)
        except (TypeError, ValueError):
            raise ValueError(f"max_tokens must be an integer, got: {resolved_max_tokens!r}")

        for _ in range(max_rounds):
            if spinner:
                console = Console()
                # Calculate word count for all messages
                word_count = sum(len(str(m.get('content', '')).split()) for m in messages if 'content' in m)
                def format_count(n):
                    if n >= 1_000_000:
                        return f"{n/1_000_000:.1f}m"
                    elif n >= 1_000:
                        return f"{n/1_000:.1f}k"
                    return str(n)
                # Count message types
                user_msgs = sum(1 for m in messages if m.get('role') == 'user')
                agent_msgs = sum(1 for m in messages if m.get('role') == 'assistant')
                tool_msgs = sum(1 for m in messages if m.get('role') == 'tool')
                # Tool uses: count tool_calls in all agent messages
                tool_uses = sum(len(m.get('tool_calls', [])) for m in messages if m.get('role') == 'assistant')
                # Tool responses: tool_msgs
                spinner_msg = (
                    f"[bold green]Waiting for AI response... ("
                    f"{format_count(word_count)} words, "
                    f"{user_msgs} user, {agent_msgs} agent, "
                    f"{tool_uses} tool uses, {tool_msgs} tool responses)"
                )
                with console.status(spinner_msg, spinner="dots") as status:
                    if runtime_config.get('vanilla_mode', False):
                        response = self.client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            max_tokens=resolved_max_tokens
                        )
                    else:
                        response = self.client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            tools=get_tool_schemas(),
                            tool_choice="auto",
                            temperature=0.2,
                            max_tokens=resolved_max_tokens
                        )
                    status.stop()
            else:
                if runtime_config.get('vanilla_mode', False):
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_tokens=resolved_max_tokens
                    )
                else:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=get_tool_schemas(),
                        tool_choice="auto",
                        temperature=0.2,
                        max_tokens=resolved_max_tokens
                    )

            if verbose_response:
                pprint.pprint(response)

            # Check for provider errors
            if hasattr(response, 'error') and response.error:
                error_msg = response.error.get('message', 'Unknown provider error')
                error_code = response.error.get('code', 'unknown')
                raise ProviderError(f"Provider error: {error_msg} (Code: {error_code})", response.error)
                
            if not response.choices:
                raise EmptyResponseError("The LLM API returned no choices in the response.")

            choice = response.choices[0]

            # Extract token usage info if available
            usage = getattr(response, 'usage', None)
            if usage:
                usage_info = {
                    'prompt_tokens': getattr(usage, 'prompt_tokens', None),
                    'completion_tokens': getattr(usage, 'completion_tokens', None),
                    'total_tokens': getattr(usage, 'total_tokens', None)
                }
            else:
                usage_info = None

            # Route content through the unified message handler if provided
            if message_handler is not None and choice.message.content:
                message_handler.handle_message(choice.message.content, msg_type="content")

            # If no tool calls, return the agent's message and usage info
            if not choice.message.tool_calls:
                # Store usage info in usage_history, linked to the next agent message index
                agent_idx = len([m for m in messages if m.get('role') == 'agent'])
                self.usage_history.append({"agent_index": agent_idx, "usage": usage_info})
                return {
                    "content": choice.message.content,
                    "usage": usage_info,
                    "usage_history": self.usage_history
                }

            tool_responses = []
            # Sequential tool execution (default, only mode)
            for tool_call in choice.message.tool_calls:
                if max_tools is not None and tool_calls_made >= max_tools:
                    raise MaxRoundsExceededError(f"Maximum number of tool calls ({max_tools}) reached in this chat session.")
                result = handle_tool_call(tool_call, message_handler=message_handler)
                tool_responses.append({"tool_call_id": tool_call.id, "content": result})
                tool_calls_made += 1

            # Store usage info in usage_history, linked to the next agent message index
            agent_idx = len([m for m in messages if m.get('role') == 'agent'])
            self.usage_history.append({"agent_index": agent_idx, "usage": usage_info})
            messages.append({"role": "assistant", "content": choice.message.content, "tool_calls": [tc.to_dict() for tc in choice.message.tool_calls]})

            for tr in tool_responses:
                messages.append({"role": "tool", "tool_call_id": tr["tool_call_id"], "content": tr["content"]})

        raise MaxRoundsExceededError("Max conversation rounds exceeded")
