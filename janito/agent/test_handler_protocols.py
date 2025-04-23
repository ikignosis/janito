from janito.agent.message_handler_protocol import MessageHandlerProtocol
from janito.agent.event_handler_protocol import EventHandlerProtocol
from janito.agent.event_dispatcher import EventDispatcher


class DummyMessageHandler(MessageHandlerProtocol):
    def __init__(self):
        self.last_message = None

    def handle_message(self, msg, msg_type=None):
        self.last_message = (msg, msg_type)


class DummyEvent:
    def __init__(self, type_, payload):
        self.type = type_
        self.payload = payload


class DummyEventHandler(EventHandlerProtocol):
    def __init__(self):
        self.last_event = None

    def handle_event(self, event):
        self.last_event = event


def test_message_handler():
    handler = DummyMessageHandler()
    handler.handle_message({"type": "info", "message": "hello"}, "info")
    assert handler.last_message[0]["message"] == "hello"
    print("MessageHandlerProtocol test passed")


def test_event_dispatcher():
    dispatcher = EventDispatcher()
    handler = DummyEventHandler()
    dispatcher.register("test", handler)
    event = DummyEvent("test", {"foo": "bar"})
    dispatcher.dispatch(event)
    assert handler.last_event.payload["foo"] == "bar"
    print("EventHandlerProtocol/EventDispatcher test passed")


if __name__ == "__main__":
    test_message_handler()
    test_event_dispatcher()
