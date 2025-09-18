from janito.cli.chat_mode.shell.commands.base import ShellCmdHandler
from janito.cli.console import shared_console


class ClearContextShellHandler(ShellCmdHandler):
    help_text = "Clear the agent's conversation history to reset context. Usage: /clear_context [optional new context message]"

    def run(self):
        try:
            # Parse optional new context message from the command line
            new_context_msg = self.after_cmd_line.strip() if self.after_cmd_line else None
            
            # Access the agent through the shell state
            if hasattr(self.shell_state, 'agent') and self.shell_state.agent:
                agent = self.shell_state.agent
                if hasattr(agent, 'conversation_history'):
                    # Clear the conversation history
                    agent.conversation_history.clear()
                    
                    # Add optional new context message if provided
                    if new_context_msg:
                        agent.conversation_history.add_message("system", new_context_msg)
                        shared_console.print("[green]✅ Agent conversation history has been cleared and new context added.[/green]")
                    else:
                        shared_console.print("[green]✅ Agent conversation history has been cleared.[/green]")
                    
                    shared_console.print("[dim]The context has been reset for this session.[/dim]")
                    return None
            
            shared_console.print("[yellow]⚠️ Could not access agent conversation history.[/yellow]")
            shared_console.print("[dim]Make sure you're in an active chat session.[/dim]")
            return None
            
        except Exception as e:
            shared_console.print(f"[red]❌ Failed to clear conversation history: {str(e)}[/red]")
            return None