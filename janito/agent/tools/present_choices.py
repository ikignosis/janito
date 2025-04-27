from typing import List
from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
import questionary
from questionary import Style

# Improved contrast: white on dark blue, bold for selected
custom_style = Style(
    [
        ("pointer", "fg:#ffffff bg:#1976d2 bold"),  # pointer: white on blue
        (
            "highlighted",
            "fg:#ffffff bg:#1565c0 bold",
        ),  # highlighted: white on dark blue, bold (matches selected)
        ("answer", "fg:#1976d2 bold"),  # answer: blue bold
        ("qmark", "fg:#1976d2 bold"),  # qmark: blue bold
    ]
)

HAND_EMOJI = "\U0001f590\ufe0f"  # 🖐️


@register_tool(name="present_choices")
class PresentChoicesTool(ToolBase):
    """
    Present a list of options to the user and return the selected option(s).

    Args:
        prompt (str): The prompt/question to display.
        choices (List[str]): List of options to present.\n            Use \\n in option text for explicit line breaks if needed.
        multi_select (bool): If True, allow multiple selections.
    Returns:
        str: The selected option(s) as a string, or a message if cancelled.
            - For multi_select=True, returns each selection on a new line, each prefixed with '- '.
            - For multi_select=False, returns the selected option as a string.
            - If cancelled, returns 'No selection made.'
    """

    def run(self, prompt: str, choices: List[str], multi_select: bool = False) -> str:
        if not choices:
            return "\u26a0\ufe0f No choices provided."
        self.report_info(f"Prompting user: {prompt} (multi_select={multi_select}) ...")
        # Use the hand emoji as the pointer symbol
        if multi_select:
            result = questionary.checkbox(
                prompt, choices=choices, style=custom_style, pointer=HAND_EMOJI
            ).ask()
            if result is None:
                return "No selection made."
            return (
                "\n".join(f"- {item}" for item in result)
                if isinstance(result, list)
                else f"- {result}"
            )
        else:
            result = questionary.select(
                prompt, choices=choices, style=custom_style, pointer=HAND_EMOJI
            ).ask()
            if result is None:
                return "No selection made."
            return str(result)
