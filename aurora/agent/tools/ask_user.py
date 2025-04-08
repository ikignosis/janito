from aurora.agent.tool_handler import ToolHandler
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style


@ToolHandler.register_tool
def ask_user(question: str) -> str:
    """
    Ask the user a question and return their response.

    question: The question to ask the user
    """
    print(f"[ask_user] {question}")

    bindings = KeyBindings()

    @bindings.add('c-r')
    def _(event):
        # Disable reverse search
        pass

    style = Style.from_dict({
        'bottom-toolbar': 'bg:#333333 #ffffff',
        'b': 'bold',
        'prompt': 'ansicyan bold',
    })

    def get_toolbar():
        return HTML('<b>Press Enter to submit. In paste mode, press Esc+Enter.</b>')

    session = PromptSession(
        multiline=True,
        key_bindings=bindings,
        editing_mode=EditingMode.EMACS,
        bottom_toolbar=get_toolbar,
        style=style
    )

    prompt_icon = HTML('<prompt>💬 </prompt>')

    response = session.prompt(prompt_icon)
    return response
