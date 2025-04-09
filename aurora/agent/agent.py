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
        import time
        from aurora.agent.conversation import ProviderError

        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                return self.conversation_handler.handle_conversation(
                    messages,
                    on_content=on_content,
                    on_tool_progress=on_tool_progress,
                    verbose_response=verbose_response,
                    spinner=spinner
                )
            except ProviderError as e:
                error_data = getattr(e, 'error_data', {}) or {}
                code = error_data.get('code', '')
                # Retry only on 5xx errors
                if isinstance(code, int) and 500 <= code < 600:
                    pass
                elif isinstance(code, str) and code.isdigit() and 500 <= int(code) < 600:
                    code = int(code)
                else:
                    raise

                if attempt < max_retries:
                    print(f"ProviderError with 5xx code encountered (attempt {attempt}/{max_retries}). Retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    print("Max retries reached. Raising error.")
                    raise
            except Exception:
                raise

