from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_registry import register_tool

@register_tool(name="ask_user")
class AskUserTool(ToolBase):
    """Ask the user a question and return their response."""
    def call(self, question: str) -> str:
        """
        Ask the user a question and return their response.

        Args:
            question (str): The question to ask the user.

        Returns:
            str: The user's response as a string. Example:
                - "Yes"
                - "No"
                - "Some detailed answer..."
        """

        from rich import print as rich_print
        from rich.panel import Panel
        from prompt_toolkit import PromptSession
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.enums import EditingMode
        from prompt_toolkit.formatted_text import HTML
        from prompt_toolkit.styles import Style

        rich_print(Panel.fit(question, title="Question", style="cyan"))

        bindings = KeyBindings()
        mode = {'multiline': False}

        @bindings.add('c-r')
        def _(event):
            pass

        style = Style.from_dict({
            'bottom-toolbar': 'bg:#333333 #ffffff',
            'b': 'bold',
            'prompt': 'bold bg:#000080 #ffffff',
        })

        def get_toolbar():
            if mode['multiline']:
                return HTML('<b>Multiline mode (Esc+Enter to submit). Type /single to switch.</b>')
            else:
                return HTML('<b>Single-line mode (Enter to submit). Type /multi for multiline.</b>')

        session = PromptSession(
            multiline=False,
            key_bindings=bindings,
            editing_mode=EditingMode.EMACS,
            bottom_toolbar=get_toolbar,
            style=style
        )

        prompt_icon = HTML('<prompt>💬 </prompt>')

        while True:
            response = session.prompt(prompt_icon)
            if not mode['multiline'] and response.strip() == '/multi':
                mode['multiline'] = True
                session.multiline = True
                continue
            elif mode['multiline'] and response.strip() == '/single':
                mode['multiline'] = False
                session.multiline = False
                continue
            else:
                return response


from janito.agent.tool_registry import register_tool
