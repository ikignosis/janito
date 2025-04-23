from typing import Protocol
from janito.agent.event import Event


class EventHandlerProtocol(Protocol):
    def handle_event(self, event: Event) -> None: ...
