import anthropic
import os
from typing import Optional
from threading import Event
from .agent import Agent

class ClaudeAIAgent(Agent):
    """Handles interaction with Claude API, including message handling"""
    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
    
    def __init__(self, system_prompt: str = None):
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        super().__init__(self.api_key, system_prompt)
        if not system_prompt:
            raise ValueError("system_prompt is required")
        
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        self.client = anthropic.Client(api_key=self.api_key)
        self.model = os.getenv('CLAUDE_MODEL', self.DEFAULT_MODEL)
        self.system_message = system_prompt
        self.last_prompt = None
        self.last_full_message = None
        self.last_response = None
        self.messages_history = []
        if system_prompt:
            self.messages_history.append(("system", system_prompt))

    def send_message(self, message: str, stop_event: Event = None) -> str:
        """Send message to Claude API and return response"""
        self.messages_history.append(("user", message))
        # Store the full message
        self.last_full_message = message
        
        try:
            # Check if already cancelled
            if stop_event and stop_event.is_set():
                return ""
            
            response = self.client.messages.create(
                model=self.model,  # Use discovered model
                system=self.system_message,
                max_tokens=8192,
                messages=[
                    {"role": "user", "content": message}
                ],
                temperature=0,
            )
            
            # Handle response
            response_text = response.content[0].text
            
            # Only store and process response if not cancelled
            if not (stop_event and stop_event.is_set()):
                self.last_response = response_text
                self.messages_history.append(("assistant", response_text))
            
            # Always return the response, let caller handle cancellation
            return response_text
            
        except KeyboardInterrupt:
            if stop_event:
                stop_event.set()
            return ""