
from abc import ABC, abstractmethod
from threading import Event
from typing import Optional, List, Tuple

class Agent(ABC):
    """Abstract base class for AI agents"""
    def __init__(self, api_key: Optional[str] = None, system_prompt: str = None):
        self.api_key = api_key
        self.system_message = system_prompt
        self.last_prompt = None
        self.last_full_message = None
        self.last_response = None
        self.messages_history: List[Tuple[str, str]] = []
        if system_prompt:
            self.messages_history.append(("system", system_prompt))

    @abstractmethod
    def send_message(self, message: str, stop_event: Event = None) -> str:
        """Send message to AI service and return response"""
        pass