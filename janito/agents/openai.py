import openai  # updated import
import os
from typing import Optional
from threading import Event
from .agent import Agent

class OpenAIAgent(Agent):
    """Handles interaction with OpenAI API, including message handling"""
    DEFAULT_MODEL = "o1-mini-2024-09-12"
    
    def __init__(self, api_key: Optional[str] = None, system_prompt: str = None):
        super().__init__(api_key, system_prompt)
        if not system_prompt:
            raise ValueError("system_prompt is required")
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        openai.api_key = self.api_key
        openai.organization = os.getenv("OPENAI_ORG")
        self.client = openai.Client()  # initialized client
        self.model = os.getenv('OPENAI_MODEL', "o1-mini-2024-09-12")  # reverted to original default model

    def send_message(self, message: str, stop_event: Event = None) -> str:
        """Send message to OpenAI API and return response"""
        self.messages_history.append(("user", message))
        self.last_full_message = message
        
        try:
            if stop_event and stop_event.is_set():
                return ""
            
            #messages = [{"role": "system", "content": self.system_message}]
            messages = [{"role": "user", "content": message}]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=4000,
                temperature=1,
            )
            
            response_text = response.choices[0].message.content
            
            if not (stop_event and stop_event.is_set()):
                self.last_response = response_text
                self.messages_history.append(("assistant", response_text))
            
            return response_text
            
        except KeyboardInterrupt:
            if stop_event:
                stop_event.set()
            return ""