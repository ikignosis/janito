import json

class MaxRoundsExceededError(Exception):
    pass


class ConversationHandler:
    def __init__(self, client, model, tool_handler):
        self.client = client
        self.model = model
        self.tool_handler = tool_handler

    def handle_conversation(self, messages, max_rounds=50, on_content=None, verbose_response=False):
        if not messages:
            raise ValueError("No prompt provided in messages")

        for _ in range(max_rounds):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tool_handler.get_tool_schemas(),
                tool_choice="auto",
                temperature=0,
                max_tokens=200000
            )

            if verbose_response:
                import pprint
                pprint.pprint(response)

            choice = response.choices[0]

            # Call the on_content callback if provided and content is not None
            if on_content is not None and choice.message.content is not None:
                on_content(choice.message.content)

            # If no tool calls, return the assistant's message
            if not choice.message.tool_calls:
                return choice.message.content

            tool_responses = []
            for tool_call in choice.message.tool_calls:
                result = self.tool_handler.handle_tool_call(tool_call, on_progress=on_content)
                tool_responses.append({"tool_call_id": tool_call.id, "content": result})

            messages.append({"role": "assistant", "content": choice.message.content, "tool_calls": [tc.to_dict() for tc in choice.message.tool_calls]})

            for tr in tool_responses:
                messages.append({"role": "tool", "tool_call_id": tr["tool_call_id"], "content": tr["content"]})

        raise MaxRoundsExceededError("Max conversation rounds exceeded")
