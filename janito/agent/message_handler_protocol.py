from typing import Protocol


class MessageHandlerProtocol(Protocol):
    def handle_message(self, msg: dict, msg_type: str = None) -> None: ...
