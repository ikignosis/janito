from typing import Callable, Dict, List
from janito.agent.event import Event, EventType


from janito.agent.event_handler_protocol import EventHandlerProtocol


class EventDispatcher:
    def __init__(self):
        self._handlers: Dict[EventType, List[Callable[[Event], None]]] = {}

    def register(self, event_type: EventType, handler: EventHandlerProtocol):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def register_all(self, handler: EventHandlerProtocol):
        # Register handler for all event types
        for event_type in EventType:
            self.register(event_type, handler)

    def dispatch(self, event: Event):
        for handler in self._handlers.get(event.type, []):
            handler.handle_event(event)
