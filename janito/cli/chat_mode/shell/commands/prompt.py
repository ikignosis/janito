from janito.cli.config import config
from janito.cli.chat_mode.shell.commands.base import ShellCmdHandler
from janito.cli.console import shared_console


class PromptShellHandler(ShellCmdHandler):
    help_text = "Show the system prompt"

    def run(self):
        agent = getattr(self.shell_state, "agent", None)
        if agent and hasattr(agent, "get_system_prompt"):
            prompt = agent.get_system_prompt()
            shared_console.print(
                f"[bold magenta]System Prompt:[/bold magenta]\n{prompt}"
            )
        else:
            shared_console.print(
                "[bold red]No LLM agent available to fetch the system prompt.[/bold red]"
            )

