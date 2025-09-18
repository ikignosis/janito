from janito.cli.chat_mode.shell.commands.base import ShellCmdHandler
from janito.cli.console import shared_console


class ClearContextShellHandler(ShellCmdHandler):
    help_text = "Clear the agent's conversation history to reset context."

    def run(self):
        try:
            # Access the agent through the shell state
            if hasattr(self.shell_state, 'agent') and self.shell_state.agent:
                agent = self.shell_state.agent
                if hasattr(agent, 'conversation_history'):
                    agent.conversation_history.clear()
                    shared_console.print("[green]✅ Agent conversation history has been cleared.[/green]")
                    shared_console.print("[dim]The context has been reset for this session.[/dim]")
                    return None
            
            shared_console.print("[yellow]⚠️ Could not access agent conversation history.[/yellow]")
            shared_console.print("[dim]Make sure you're in an active chat session.[/dim]")
            return None
            
        except Exception as e:
            shared_console.print(f"[red]❌ Failed to clear conversation history: {str(e)}[/red]")
            return None