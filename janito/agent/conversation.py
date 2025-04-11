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

    def handle_conversation(self, messages, max_rounds=50, on_content=None, on_tool_progress=None, verbose_response=False, spinner=False, max_tokens=None):
        if not messages:
            raise ValueError("No prompt provided in messages")

        from rich.console import Console
        console = Console()

        from janito.agent.config import effective_config

        # Resolve max_tokens priority: runtime param > config > default
        resolved_max_tokens = max_tokens
        if resolved_max_tokens is None:
            resolved_max_tokens = effective_config.get('max_tokens', 200000)

        for _ in range(max_rounds):
            if spinner:
                with console.status("[bold green]Waiting for AI response...", spinner="dots") as status:
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
                return {
    "content": choice.message.content,
    "usage": usage_info
}

            tool_responses = []
            for tool_call in choice.message.tool_calls:
                result = self.tool_handler.handle_tool_call(tool_call, on_progress=on_tool_progress)
                tool_responses.append({"tool_call_id": tool_call.id, "content": result})

            messages.append({"role": "assistant", "content": choice.message.content, "tool_calls": [tc.to_dict() for tc in choice.message.tool_calls]})

            for tr in tool_responses:
                messages.append({"role": "tool", "tool_call_id": tr["tool_call_id"], "content": tr["content"]})

        raise MaxRoundsExceededError("Max conversation rounds exceeded")
