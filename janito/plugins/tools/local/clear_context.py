"""
Clear Context Tool for Janito

This tool clears the agent's conversation history, effectively resetting the context
for the current chat session. This is useful when you want to start fresh without
restarting the entire session.
"""

from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction


class ClearContextTool(ToolBase):
    """
    Clear the agent's conversation history to reset context.
    
    This tool clears the LLM's conversation history, allowing you to start fresh
    within the current session without losing session state or tool configurations.
    """

    tool_name = "clear_context"
    permissions = ToolPermissions(read=False, write=False, execute=False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent = None
    
    def set_agent(self, agent):
        """Set the agent reference to access conversation history."""
        self._agent = agent

    def run(self, new_context_msg: str = None) -> str:
        """
        Clear the agent's conversation history.
        
        Parameters
        ----------
        new_context_msg : str, optional
            Optional message to add to the conversation history after clearing.
            This can be used to provide context about the reset.
        
        Returns
        -------
        str
            Success message confirming the context has been cleared.
        """
        self.report_action("Clearing agent conversation history", None)
        
        try:
            # Determine which agent reference to use
            agent = None
            if self._agent and hasattr(self._agent, 'conversation_history'):
                agent = self._agent
            elif hasattr(self, '_tools_adapter') and hasattr(self._tools_adapter, 'agent'):
                agent = self._tools_adapter.agent
            elif hasattr(self, 'agent') and hasattr(self.agent, 'conversation_history'):
                agent = self.agent
            
            if agent and hasattr(agent, 'conversation_history'):
                # Clear the conversation history
                agent.conversation_history.clear()
                
                # Add optional new context message if provided
                if new_context_msg:
                    agent.conversation_history.add_message("system", new_context_msg)
                
                self.report_success("Agent conversation history cleared successfully")
                
                if new_context_msg:
                    return f"✅ Agent conversation history has been cleared and new context added. The context has been reset."
                else:
                    return "✅ Agent conversation history has been cleared. The context has been reset."
            
            # Try to access through the event bus or global context
            # This is a fallback approach for when the tool is called directly
            try:
                from janito.cli.chat_mode.session import ChatSession
                # Try to find the current session through global state
                # This is a workaround for the architectural limitation
                
                # For now, provide a clear message about the limitation
                # and suggest using the shell command instead
                self.report_warning("Use /clear_context command instead")
                return "⚠️ Cannot clear conversation history from tool context. Please use the /clear_context shell command instead. This tool is designed to work within the chat session context."
                
            except ImportError:
                pass
            
            # Final fallback message
            self.report_warning("Cannot access agent conversation history from tool context")
            return "⚠️ Cannot clear conversation history: the tool does not have access to the agent context. Please use the /clear_context shell command instead."
                
        except Exception as e:
            self.report_error(f"Failed to clear conversation history: {str(e)}")
            return f"❌ Failed to clear conversation history: {str(e)}"