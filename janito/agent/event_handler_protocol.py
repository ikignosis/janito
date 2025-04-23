from typing import Protocol, Any


class EventHandlerProtocol(Protocol):
    def handle_event(self, event: Any) -> None: ...
