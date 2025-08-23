import threading
from abc import ABC, abstractmethod
from queue import Queue
from janito.llm.driver_input import DriverInput
from janito.driver_events import (
    RequestStarted,
    RequestFinished,
    ResponseReceived,
    RequestStatus,
)


class LLMDriver(ABC):
    def clear_output_queue(self):
        """Remove all items from the output queue."""
        try:
            while True:
                self.output_queue.get_nowait()
        except Exception:
            pass

    def clear_input_queue(self):
        """Remove all items from the input queue."""
        try:
            while True:
                self.input_queue.get_nowait()
        except Exception:
            pass

    """
    Abstract base class for LLM drivers (threaded, queue-based).
    Subclasses must implement:
      - _call_api: Call provider API with DriverInput.
      - _convert_completion_message_to_parts: Convert provider message to MessagePart objects.
      - convert_history_to_api_messages: Convert LLMConversationHistory to provider-specific messages format for API calls.
    Workflow:
      - Accept DriverInput via input_queue.
      - Put DriverEvents on output_queue.
      - Use start() to launch worker loop in a thread.
    The driver automatically creates its own input/output queues, accessible via .input_queue and .output_queue.
    """

    available = True
    unavailable_reason = None

    def __init__(self, tools_adapter=None, provider_name=None):
        self.input_queue = Queue()
        self.output_queue = Queue()
        self._thread = None
        self.tools_adapter = tools_adapter
        self.provider_name = provider_name

    def start(self):
        """Validate tool schemas (if any) and launch the driver's background thread to process DriverInput objects."""
        # Validate all tool schemas before starting the thread
        if self.tools_adapter is not None:
            from janito.tools.tools_schema import ToolSchemaBase

            validator = ToolSchemaBase()
            for tool in self.tools_adapter.get_tools():
                # Validate the tool's class (not instance)
                validator.validate_tool_class(tool.__class__)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while True:
            driver_input = self.input_queue.get()
            if driver_input is None:
                break  # Sentinel received, exit thread
            try:
                # Only process if driver_input is a DriverInput instance
                if isinstance(driver_input, DriverInput):
                    self.process_driver_input(driver_input)
                else:
                    # Optionally log or handle unexpected input types
                    pass
            except Exception as e:
                import traceback

                self.output_queue.put(
                    RequestFinished(
                        driver_name=self.__class__.__name__,
                        request_id=getattr(driver_input.config, "request_id", None),
                        status=RequestStatus.ERROR,
                        error=str(e),
                        exception=e,
                        traceback=traceback.format_exc(),
                    )
                )

    def handle_driver_unavailable(self, request_id):
        self.output_queue.put(
            RequestFinished(
                driver_name=self.__class__.__name__,
                request_id=request_id,
                status=RequestStatus.ERROR,
                error=self.unavailable_reason,
                exception=ImportError(self.unavailable_reason),
                traceback=None,
            )
        )

    def emit_response_received(
        self, driver_name, request_id, result, parts, timestamp=None, metadata=None
    ):
        self.output_queue.put(
            ResponseReceived(
                driver_name=driver_name,
                request_id=request_id,
                parts=parts,
                tool_results=[],
                timestamp=timestamp,
                metadata=metadata or {},
            )
        )
        # Debug: print summary of parts by type
        if hasattr(self, "config") and getattr(self.config, "verbose_api", False):
            from collections import Counter

            type_counts = Counter(type(p).__name__ for p in parts)
            print(
                f"[verbose-api] Emitting ResponseReceived with parts: {dict(type_counts)}",
                flush=True,
            )

    def process_driver_input(self, driver_input: DriverInput):

        config = driver_input.config
        request_id = getattr(config, "request_id", None)
        if not self.available:
            self.handle_driver_unavailable(request_id)
            return
        # Prepare payload for RequestStarted event
        payload = {"provider_name": self.provider_name}
        if hasattr(config, "model") and getattr(config, "model", None):
            payload["model"] = getattr(config, "model")
        elif hasattr(config, "model_name") and getattr(config, "model_name", None):
            payload["model"] = getattr(config, "model_name")
        self.output_queue.put(
            RequestStarted(
                driver_name=self.__class__.__name__,
                request_id=request_id,
                payload=payload,
            )
        )
        # Check for cancel_event before starting
        if (
            hasattr(driver_input, "cancel_event")
            and driver_input.cancel_event is not None
            and driver_input.cancel_event.is_set()
        ):
            self.output_queue.put(
                RequestFinished(
                    driver_name=self.__class__.__name__,
                    request_id=request_id,
                    status=RequestStatus.CANCELLED,
                    reason="Canceled before start",
                )
            )
            return
        try:
            result = self._call_api(driver_input)
            # If result is None and cancel_event is set, treat as cancelled
            if (
                hasattr(driver_input, "cancel_event")
                and driver_input.cancel_event is not None
                and driver_input.cancel_event.is_set()
            ):
                self.output_queue.put(
                    RequestFinished(
                        driver_name=self.__class__.__name__,
                        request_id=request_id,
                        status=RequestStatus.CANCELLED,
                        reason="Cancelled during processing (post-API)",
                    )
                )
                return
            if (
                result is None
                and hasattr(driver_input, "cancel_event")
                and driver_input.cancel_event is not None
                and driver_input.cancel_event.is_set()
            ):
                # Already handled by driver
                return
            # Check for cancel_event after API call (subclasses should also check during long calls)
            if (
                hasattr(driver_input, "cancel_event")
                and driver_input.cancel_event is not None
                and driver_input.cancel_event.is_set()
            ):
                self.output_queue.put(
                    RequestFinished(
                        driver_name=self.__class__.__name__,
                        request_id=request_id,
                        status=RequestStatus.CANCELLED,
                        reason="Canceled during processing",
                    )
                )
                return
            message = self._get_message_from_result(result)
            parts = (
                self._convert_completion_message_to_parts(message) if message else []
            )
            timestamp = getattr(result, "created", None)
            metadata = {"usage": getattr(result, "usage", None), "raw_response": result}
            self.emit_response_received(
                self.__class__.__name__, request_id, result, parts, timestamp, metadata
            )
        except Exception as ex:
            import traceback

            self.output_queue.put(
                RequestFinished(
                    driver_name=self.__class__.__name__,
                    request_id=request_id,
                    status=RequestStatus.ERROR,
                    error=str(ex),
                    exception=ex,
                    traceback=traceback.format_exc(),
                )
            )

    @abstractmethod
    def _prepare_api_kwargs(self, config, conversation):
        """
        Subclasses must implement: Prepare API kwargs for the provider, including any tool schemas if needed.
        """
        pass

    @abstractmethod
    def _call_api(self, driver_input: DriverInput):
        """Subclasses implement: Use driver_input to call provider and return result object."""
        pass

    @abstractmethod
    def _convert_completion_message_to_parts(self, message):
        """Subclasses implement: Convert provider message to list of MessagePart objects."""
        pass

    @abstractmethod
    def convert_history_to_api_messages(self, conversation_history):
        """
        Subclasses implement: Convert LLMConversationHistory to the messages object required by their provider API.
        :param conversation_history: LLMConversationHistory instance
        :return: Provider-specific messages object (e.g., list of dicts for OpenAI)
        """
        pass

    @abstractmethod
    def _get_message_from_result(self, result):
        """Extract the message object from the provider result. Subclasses must implement this."""
        raise NotImplementedError("Subclasses must implement _get_message_from_result.")

    def cancel_current_request(self):
        """Cancel the current request being processed."""
        # Use global cancellation manager to cancel the current request
        from janito.llm.cancellation_manager import get_cancellation_manager

        cancel_manager = get_cancellation_manager()
        cancel_manager.cancel_current_request()
