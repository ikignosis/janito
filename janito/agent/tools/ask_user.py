from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool


@register_tool(name="ask_user")
class AskUserTool(ToolBase):
    """
    Request clarification or input from the user whenever there is uncertainty, ambiguity, missing information, or multiple valid options. Returns the user's response as a string.

    Args:
        question (str): The question to ask the user.
    Returns:
        str: The user's response as a string. Example:
            - "Yes"
            - "No"
            - "Some detailed answer..."
    """

    def call(self, question: str) -> str:
        from rich import print as rich_print
        from rich.panel import Panel
        from prompt_toolkit import PromptSession
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.enums import EditingMode
        from prompt_toolkit.formatted_text import HTML
        from prompt_toolkit.styles import Style

        rich_print(Panel.fit(question, title="Question", style="cyan"))

        bindings = KeyBindings()
        mode = {"multiline": False}

        @bindings.add("c-r")
        def _(event):
            pass

        @bindings.add("f12")
        def _(event):
            """When F12 is pressed, send 'proceed' as input immediately."""
            buf = event.app.current_buffer
            buf.text = "proceed"
            buf.validate_and_handle()

        style = Style.from_dict(
            {
                "bottom-toolbar": "bg:#333333 #ffffff",
                "b": "bold",
                "prompt": "bold bg:#000080 #ffffff",
            }
        )

        def get_toolbar():
            f12_hint = " Press <b>F12</b> to auto-fill 'proceed' and submit."
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

        prompt_icon = HTML("<prompt>💬 </prompt>")

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
                return response
