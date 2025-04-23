from janito.agent.event_dispatcher import EventDispatcher
from janito.agent.rich_message_handler import RichMessageHandler

# Singleton dispatcher
shared_event_dispatcher = EventDispatcher()

# Register handlers (example: RichMessageHandler for all events)
rich_handler = RichMessageHandler()
shared_event_dispatcher.register_all(rich_handler)

# You can register other handlers as needed, e.g.:
# queued_handler = QueuedMessageHandler(...)
# shared_event_dispatcher.register_all(queued_handler)
# queue_handler = QueueMessageHandler(...)
# shared_event_dispatcher.register_all(queue_handler)
