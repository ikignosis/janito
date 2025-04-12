"""Agent module: defines the core LLM agent with tool and conversation handling."""

import os
import json
from openai import OpenAI
from janito.agent.conversation import ConversationHandler
from janito.agent.tool_handler import ToolHandler

class Agent:
    """LLM Agent capable of handling conversations and tool calls."""

    REFERER = "www.janito.dev"
    TITLE = "Janito"

    def __init__(
        self,
        api_key: str,
        model: str = None,
        system_prompt: str | None = None,
        verbose_tools: bool = False,
        tool_handler = None,
        base_url: str = "https://openrouter.ai/api/v1"
    ):
        """
        Initialize the Agent.

        Args:
            api_key: API key for OpenAI-compatible service.
            model: Model name to use.
            system_prompt: Optional system prompt override.
            verbose_tools: Enable verbose tool call logging.
            tool_handler: Optional custom ToolHandler instance.
            base_url: API base URL.
        """
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        if os.environ.get("USE_AZURE_OPENAI"):
            from openai import AzureOpenAI
            self.client = AzureOpenAI(
                api_key=api_key,
                azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
                api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2023-05-15"),
            )
        else:
            self.client = OpenAI(
                base_url=base_url,
                api_key=api_key,
                default_headers={
                    "HTTP-Referer": self.REFERER,
                    "X-Title": self.TITLE
                }
            )
        if tool_handler is not None:
            self.tool_handler = tool_handler
        else:
            self.tool_handler = ToolHandler(verbose=verbose_tools)

        self.conversation_handler = ConversationHandler(
            self.client, self.model, self.tool_handler
        )

    def chat(self, messages, on_content=None, on_tool_progress=None, verbose_response=False, spinner=False, max_tokens=None):
        import time
        from janito.agent.conversation import ProviderError

        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                return self.conversation_handler.handle_conversation(
                    messages,
                    max_tokens=max_tokens,
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
