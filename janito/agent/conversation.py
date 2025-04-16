import json

class MaxRoundsExceededError(Exception):
    pass

class EmptyResponseError(Exception):
    pass

class ProviderError(Exception):
    def __init__(self, message, error_data):
        self.error_data = error_data
        super().__init__(message)

class ConversationHandler:
    def __init__(self, client, model, tool_handler):
        self.client = client
        self.model = model
        self.tool_handler = tool_handler
        self.usage_history = []

    def handle_conversation(self, messages, max_rounds=50, on_content=None, on_tool_progress=None, verbose_response=False, spinner=False, max_tokens=None):
        from janito.agent.runtime_config import runtime_config
        max_tools = runtime_config.get('max_tools', None)
        tool_calls_made = 0
        if not messages:
            raise ValueError("No prompt provided in messages")

        from rich.console import Console
        console = Console()

        from janito.agent.runtime_config import unified_config

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
                                # Calculate word count for all messages
                word_count = sum(len(str(m.get('content', '')).split()) for m in messages if 'content' in m)
                spinner_msg = f"[bold green]Waiting for AI response... ({word_count} words in conversation)"
                with console.status(spinner_msg, spinner="dots") as status:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=self.tool_handler.get_tool_schemas(),
                        tool_choice="auto",
                        temperature=0.2,
                        max_tokens=resolved_max_tokens
                    )
                    status.stop()
                    # console.print("\r\033[2K", end="")  # Clear the spinner line removed
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tool_handler.get_tool_schemas(),
                    tool_choice="auto",
                    temperature=0.2,
                    max_tokens=resolved_max_tokens
                )

            if verbose_response:
                import pprint
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

            # Call the on_content callback if provided and content is not None
            if on_content is not None and choice.message.content is not None:
                on_content({"content": choice.message.content})

            # If no tool calls, return the assistant's message and usage info
            if not choice.message.tool_calls:
                # Store usage info in usage_history, linked to the next assistant message index
                assistant_idx = len([m for m in messages if m.get('role') == 'assistant'])
                self.usage_history.append({"assistant_index": assistant_idx, "usage": usage_info})
                return {
                    "content": choice.message.content,
                    "usage": usage_info,
                    "usage_history": self.usage_history
                }

            from janito.agent.runtime_config import runtime_config
            tool_responses = []
            # Sequential tool execution (default, only mode)
            for tool_call in choice.message.tool_calls:
                if max_tools is not None and tool_calls_made >= max_tools:
                    raise MaxRoundsExceededError(f"Maximum number of tool calls ({max_tools}) reached in this chat session.")
                result = self.tool_handler.handle_tool_call(tool_call, on_progress=on_tool_progress)
                tool_responses.append({"tool_call_id": tool_call.id, "content": result})
                tool_calls_made += 1

            # Store usage info in usage_history, linked to the next assistant message index
            assistant_idx = len([m for m in messages if m.get('role') == 'assistant'])
            self.usage_history.append({"assistant_index": assistant_idx, "usage": usage_info})
            messages.append({"role": "assistant", "content": choice.message.content, "tool_calls": [tc.to_dict() for tc in choice.message.tool_calls]})

            for tr in tool_responses:
                messages.append({"role": "tool", "tool_call_id": tr["tool_call_id"], "content": tr["content"]})

        raise MaxRoundsExceededError("Max conversation rounds exceeded")
