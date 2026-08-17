#!/usr/bin/env python3
"""
AskUser Tool - Prompts the user with a question and returns their answer.

This tool allows the AI agent to ask the user a question interactively
in the console and receive their answer as the tool result.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.system.ask_user [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import json
from typing import Any

from ...tooling import BaseTool
from ...tooling.decorator import tool


@tool(permissions="r")
class AskUser(BaseTool):
    """
    Tool for asking the user a question and returning their answer.

    Use this tool when you need to gather information from the user
    interactively, such as clarifications, confirmations, or input values.
    """

    def run(self, question: str) -> dict[str, Any]:
        """
        Prompt the user with a question and return their answer.

        Args:
            question (str): The question to display to the user.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating the interaction completed
                - 'question': the question that was asked
                - 'answer': the user's response (empty string if the input
                  ended, e.g. piped input / Ctrl+D)
                - 'error': error message (only present if success is False)

        Note:
            Pressing Ctrl+C while the question is awaiting an answer does
            *not* produce a result: the ``KeyboardInterrupt`` propagates and
            interrupts the in-flight LLM conversation turn (the agent loop
            rolls the conversation history back).
        """
        try:
            answer = self.prompt_user(question)

            self.report_result(
                f"User answered: {answer}" if answer else "User provided no answer"
            )

            return {
                "success": True,
                "question": question,
                "answer": answer,
            }

        except Exception as e:
            self.report_error(f"Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "question": question,
            }


# ── CLI testing harness ─────────────────────────────────────────────────────────────
def main():
    """Command line interface for testing the AskUser tool."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Ask the user a question and return their answer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "What is your name?"
  %(prog)s "Pick a number" --json
        """,
    )

    parser.add_argument("question", help="The question to ask the user")
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )

    args = parser.parse_args()

    result = AskUser().run(question=args.question)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"  Question: {result['question']}")
            print(f"  Answer:   {result['answer']}")
        else:
            print(f"  ❌ Failed: {result.get('error', 'Unknown error')}")

    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit(main())
