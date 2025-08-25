from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.tools.adapters.local.adapter import register_local_tool
from janito.tools.loop_protection_decorator import protect_against_loops

from rich import print as rich_print
from janito.i18n import tr
from rich.panel import Panel
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.formatted_text import HTML
from janito.cli.chat_mode.prompt_style import chat_shell_style
from prompt_toolkit.styles import Style

toolbar_style = Style.from_dict({"bottom-toolbar": "fg:yellow bg:darkred"})


@register_local_tool
class AskUserTool(ToolBase):
    """
    Prompts the user for clarification or input with a question.

    Args:
        question (str): The question to ask the user. This parameter is required and should be a string containing the prompt or question to display to the user.
    Returns:
        str: The user's response as a string. Example:
            - "Yes"
            - "No"
            - "Some detailed answer..."
    """

    permissions = ToolPermissions(read=True)
    tool_name = "ask_user"

    @protect_against_loops(max_calls=5, time_window=10.0, key_field="question")
    def run(self, question: str) -> str:

        print()  # Print an empty line before the question panel
        rich_print(Panel.fit(question, title=tr("Question"), style="cyan"))

        bindings = KeyBindings()
        mode = {"multiline": False}

        @bindings.add("c-r")
        def _(event):
            pass

        @bindings.add("f12")
        def _(event):
            buf = event.app.current_buffer
            buf.text = "Do It"
            buf.validate_and_handle()

        @bindings.add("f2")
        def _(event):
            buf = event.app.current_buffer
            buf.text = "F2"
            buf.validate_and_handle()

        # Use shared CLI styles

        # prompt_style contains the prompt area and input background
        # toolbar_style contains the bottom-toolbar styling

        # Use the shared chat_shell_style for input styling only
        style = chat_shell_style

        def get_toolbar():
            f12_hint = " F2: F2 | F12: Do It"
            if mode["multiline"]:
                return HTML(
                    f"<b>Multiline mode (Esc+Enter to submit). Type /single to switch.</b>{f12_hint}"
                )
            else:
                return HTML(
                    f"<b>Single-line mode (Enter to submit). Type /multi for multiline.</b>{f12_hint}"
                )

        session = PromptSession(
            multiline=False,
            key_bindings=bindings,
            editing_mode=EditingMode.EMACS,
            bottom_toolbar=get_toolbar,
            style=style,
        )

        prompt_icon = HTML("<inputline>💬 </inputline>")

        while True:
            response = session.prompt(prompt_icon)
            if not mode["multiline"] and response.strip() == "/multi":
                mode["multiline"] = True
                session.multiline = True
                continue
            elif mode["multiline"] and response.strip() == "/single":
                mode["multiline"] = False
                session.multiline = False
                continue
            else:
                sanitized = response.strip()
                try:
                    sanitized.encode("utf-8")
                except UnicodeEncodeError:
                    sanitized = sanitized.encode("utf-8", errors="replace").decode(
                        "utf-8"
                    )
                    rich_print(
                        "[yellow]Warning: Some characters in your input were not valid UTF-8 and have been replaced.[/yellow]"
                    )
                return sanitized
