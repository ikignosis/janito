"""
/ask command handler - sends an individual question to the LLM with a fresh chat history.

Each invocation of /ask creates its own isolated chat history initialized with
a system prompt, so it does not pollute the main conversation history.
"""

from .base import CmdHandler
from .registry import register_command


class AskCmdHandler(CmdHandler):
    """Command handler for /ask command - individual questions to the LLM."""

    @property
    def name(self) -> str:
        return "/ask"

    def handle(self, shell, user_input: str) -> bool:
        """Handle the /ask command."""
        # Match '/ask' exactly or '/ask <question>' (not '/askme', etc.)
        if user_input.lower() != self.name.lower() and not user_input.lower().startswith(self.name.lower() + " "):
            return False

        # Extract the question (everything after '/ask ')
        question = user_input[len(self.name):].strip()

        if not question:
            print("\nUsage: /ask <your question>")
            print("  Sends an individual question to the LLM with a fresh chat history.")
            print("  The chat history is cleared on every /ask invocation.\n")
            return True

        self._ask(shell, question)
        return True

    def _ask(self, shell, question: str) -> None:
        """Send an individual question to the LLM with a fresh, isolated chat history."""
        # Create a fresh chat history for this question, cleared on every command
        ask_history = [
            {"role": "system", "content": "You are an helpful assistant"}
        ]

        # Ensure send_prompt_func is available on the shell
        send_prompt_func = getattr(shell, "send_prompt_func", None)
        if send_prompt_func is None:
            print("\nError: No prompt function available. Are you in an active session?\n")
            return

        verbose = getattr(shell, "verbose", False)
        thinking = getattr(shell, "thinking", False)

        print()
        try:
            response = send_prompt_func(
                question,
                verbose=verbose,
                previous_messages=ask_history,
                tools=[],
                thinking=thinking,
            )
        except KeyboardInterrupt:
            print("Request interrupted")
        except Exception as e:
            print(f"Error: {e}")


# Register this handler
_handler = AskCmdHandler()
register_command(_handler)
