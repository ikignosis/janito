import os
import json
from openai import OpenAI
from aurora.agent.conversation import ConversationHandler
from aurora.agent.tool_handler import ToolHandler

class Agent:
    def __init__(
        self,
        api_key: str,
        model: str = "openrouter/quasar-alpha",
        system_prompt: str | None = None,
        verbose_tools: bool = False,
        tool_handler: ToolHandler | None = None
    ):
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        if tool_handler is not None:
            self.tool_handler = tool_handler
        else:
            self.tool_handler = ToolHandler(verbose=verbose_tools)

        self.conversation_handler = ConversationHandler(
            self.client, self.model, self.tool_handler
        )

    def chat(self, messages, on_content=None, on_tool_progress=None, verbose_response=False, spinner=False):
        if spinner:
            from rich.console import Console
            console = Console()
            with console.status("[bold green]Waiting for AI response...", spinner="dots") as status:
                response = self.conversation_handler.handle_conversation(
                    messages,
                    on_content=on_content,
                    on_tool_progress=on_tool_progress,
                    verbose_response=verbose_response
                )
                status.stop()
                return response
        else:
            return self.conversation_handler.handle_conversation(
                messages,
                on_content=on_content,
                on_tool_progress=on_tool_progress,
                verbose_response=verbose_response
            )
