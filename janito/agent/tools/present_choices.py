from typing import List
from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.i18n import tr
import questionary
from questionary import Style

custom_style = Style(
    [
        ("pointer", "fg:#ffffff bg:#1976d2 bold"),
        ("highlighted", "fg:#ffffff bg:#1565c0 bold"),
        ("answer", "fg:#1976d2 bold"),
        ("qmark", "fg:#1976d2 bold"),
    ]
)
HAND_EMOJI = "🖐️"  # 🖐️


@register_tool(name="present_choices")
class PresentChoicesTool(ToolBase):
    """
    Present a list of options to the user and return the selected option(s).

    Args:
        prompt (str): The prompt/question to display.
        choices (List[str]): List of options to present. Use \n in option text for explicit line breaks if needed.
        multi_select (bool): If True, allow multiple selections.
    Returns:
        str: The selected option(s) as a string, or a message if cancelled.
            - For multi_select=True, returns each selection on a new line, each prefixed with '- '.
            - For multi_select=False, returns the selected option as a string.
            - If cancelled, returns 'No selection made.'
    """

    def run(self, prompt: str, choices: List[str], multi_select: bool = False) -> str:
        if not choices:
            return tr("⚠️ No choices provided.")
        self.report_info(
            tr(
                "ℹ️ Prompting user: {prompt} (multi_select={multi_select}) ...",
                prompt=prompt,
                multi_select=multi_select,
            )
        )
        if multi_select:
            result = questionary.checkbox(
                prompt, choices=choices, style=custom_style, pointer=HAND_EMOJI
            ).ask()
            if result is None:
                return tr("No selection made.")
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
                return tr("No selection made.")
            return str(result)
