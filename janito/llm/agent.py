from janito.llm.driver_input import DriverInput
from janito.llm.driver_config import LLMDriverConfig
from janito.conversation_history import LLMConversationHistory
from janito.tools.tools_adapter import ToolsAdapterBase
from queue import Queue, Empty
from janito.driver_events import RequestStatus
from typing import Any, Optional, List, Iterator, Union
import threading
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
import time
from janito.event_bus.bus import event_bus


class LLMAgent:
    _event_lock: threading.Lock
    _latest_event: Optional[str]

    @property
    def template_vars(self):
        if not hasattr(self, "_template_vars"):
            self._template_vars = {}
        return self._template_vars

    """
    Represents an agent that interacts with an LLM driver to generate responses.
    Maintains conversation history as required by the new driver interface.
    """

    def __init__(
        self,
        llm_provider,
        tools_adapter: ToolsAdapterBase,
        agent_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        conversation_history: Optional[LLMConversationHistory] = None,
        input_queue: Queue = None,
        output_queue: Queue = None,
        verbose_agent: bool = False,
        **kwargs: Any,
    ):
        self.llm_provider = llm_provider
        self.tools_adapter = tools_adapter
        self.agent_name = agent_name
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.conversation_history = conversation_history or LLMConversationHistory()
        self.input_queue = input_queue if input_queue is not None else Queue()
        self.output_queue = output_queue if output_queue is not None else Queue()
        self._event_lock = threading.Lock()
        self._latest_event = None
        self.verbose_agent = verbose_agent
        self.driver = None  # Will be set by setup_agent if available

    def get_provider_name(self):
        # Try to get provider name from driver, fallback to llm_provider, else '?'
        if self.driver and hasattr(self.driver, "name"):
            return self.driver.name
        elif hasattr(self.llm_provider, "name"):
            return self.llm_provider.name
        return "?"

    def get_model_name(self):
        # Try to get model name from driver, fallback to llm_provider, else '?'
        if self.driver and hasattr(self.driver, "model_name"):
            return self.driver.model_name
        elif hasattr(self.llm_provider, "model_name"):
            return self.llm_provider.model_name
        return "?"

    def set_template_var(self, key: str, value: str) -> None:
        """Set a variable for system prompt templating."""
        if not hasattr(self, "_template_vars"):
            self._template_vars = {}
        self._template_vars[key] = value

    def set_system_prompt(self, prompt: str) -> None:
        self.system_prompt = prompt

    def set_system_using_template(self, template_path: str, **kwargs) -> None:
        env = Environment(
            loader=FileSystemLoader(Path(template_path).parent),
            autoescape=select_autoescape(),
        )
        template = env.get_template(Path(template_path).name)
        self.system_prompt = template.render(**kwargs)

    def refresh_system_prompt_from_template(self):
        if hasattr(self, "_template_vars") and hasattr(self, "system_prompt_template"):
            env = Environment(
                loader=FileSystemLoader(Path(self.system_prompt_template).parent),
                autoescape=select_autoescape(),
            )
            template = env.get_template(Path(self.system_prompt_template).name)
            # Refresh allowed_permissions in context before rendering
            from janito.tools.permissions import get_global_allowed_permissions
            from janito.tools.tool_base import ToolPermissions

            perms = get_global_allowed_permissions()
            if isinstance(perms, ToolPermissions):
                perm_str = ""
                if perms.read:
                    perm_str += "r"
                if perms.write:
                    perm_str += "w"
                if perms.execute:
                    perm_str += "x"
                self._template_vars["allowed_permissions"] = perm_str or None
            else:
                self._template_vars["allowed_permissions"] = perms
            self.system_prompt = template.render(**self._template_vars)

    def get_system_prompt(self) -> str:
        return self.system_prompt

    def _add_prompt_to_history(self, prompt_or_messages, role):
        if isinstance(prompt_or_messages, str):
            self.conversation_history.add_message(role, prompt_or_messages)
        elif isinstance(prompt_or_messages, list):
            for msg in prompt_or_messages:
                self.conversation_history.add_message(
                    msg.get("role", role), msg.get("content", "")
                )

    def _ensure_system_prompt(self):
        if self.system_prompt and (
            not self.conversation_history._history
            or self.conversation_history._history[0]["role"] != "system"
        ):
            self.conversation_history._history.insert(
                0, {"role": "system", "content": self.system_prompt}
            )

    def _validate_and_update_history(
        self,
        prompt: str = None,
        messages: Optional[List[dict]] = None,
        role: str = "user",
    ):
        if prompt is None and not messages:
            raise ValueError(
                "Either prompt or messages must be provided to Agent.chat."
            )
        if prompt is not None:
            self._add_prompt_to_history(prompt, role)
        elif messages:
            self._add_prompt_to_history(messages, role)

    def _log_event_verbose(self, event):
        if getattr(self, "verbose_agent", False):
            if hasattr(event, "parts"):
                for i, part in enumerate(getattr(event, "parts", [])):
                    pass  # Add detailed logging here if needed
            else:
                pass  # Add detailed logging here if needed

    def _handle_event_type(self, event):
        event_class = getattr(event, "__class__", None)
        if event_class is not None and event_class.__name__ == "ResponseReceived":
            added_tool_results = self._handle_response_received(event)
            return event, added_tool_results
        # For all other events (including RequestFinished with status='error', RequestStarted), do not exit loop
        return None, False

    def _prepare_driver_input(self, config, cancel_event=None):
        return DriverInput(
            config=config,
            conversation_history=self.conversation_history,
            cancel_event=cancel_event,
        )

    def _process_next_response(
        self, poll_timeout: float = 1.0, max_wait_time: float = 600.0
    ):
        """
        Wait for a single event from the output queue (with timeout), process it, and return the result.
        This function is intended to be called from the main agent loop, which controls the overall flow.
        """
        if getattr(self, "verbose_agent", False):
            print("[agent] [DEBUG] Entered _process_next_response")
        elapsed = 0.0
        if getattr(self, "verbose_agent", False):
            print("[agent] [DEBUG] Waiting for event from output_queue...")
        # Let KeyboardInterrupt propagate to caller
        return self._poll_for_event(poll_timeout, max_wait_time)

    def _poll_for_event(self, poll_timeout, max_wait_time):
        elapsed = 0.0
        while True:
            event = self._get_event_from_output_queue(poll_timeout)
            if event is None:
                elapsed += poll_timeout
                if elapsed >= max_wait_time:
                    error_msg = f"[ERROR] No output from driver in agent.chat() after {max_wait_time} seconds (timeout exit)"
                    print(error_msg)
                    print("[DEBUG] Exiting _process_next_response due to timeout")
                    return None, False
                continue
            if getattr(self, "verbose_agent", False):
                print(f"[agent] [DEBUG] Received event from output_queue: {event}")
            event_bus.publish(event)
            self._log_event_verbose(event)
            event_class = getattr(event, "__class__", None)
            event_name = event_class.__name__ if event_class else None
            if event_name == "ResponseReceived":
                result = self._handle_event_type(event)
                return result
            elif event_name == "RequestFinished" and getattr(event, "status", None) in [
                RequestStatus.ERROR,
                RequestStatus.EMPTY_RESPONSE,
                RequestStatus.TIMEOUT,
            ]:
                return (event, False)

    def _get_event_from_output_queue(self, poll_timeout):
        try:
            return self.output_queue.get(timeout=poll_timeout)
        except Empty:
            return None

    def _handle_response_received(self, event) -> bool:
        """
        Handle a ResponseReceived event: execute tool calls if present, update history.
        Returns True if the agent loop should continue (tool calls found), False otherwise.
        """
        if getattr(self, "verbose_agent", False):
            print("[agent] [INFO] Handling ResponseReceived event.")
        from janito.llm.message_parts import FunctionCallMessagePart

        # Skip tool processing if no tools adapter is available
        if self.tools_adapter is None:
            if getattr(self, "verbose_agent", False):
                print("[agent] [DEBUG] No tools adapter available, skipping tool calls")
            return False

        tool_calls = []
        tool_results = []
        for part in event.parts:
            if isinstance(part, FunctionCallMessagePart):
                if getattr(self, "verbose_agent", False):
                    print(
                        f"[agent] [DEBUG] Tool call detected: {getattr(part, 'name', repr(part))} with arguments: {getattr(part, 'arguments', None)}"
                    )
                tool_calls.append(part)
                try:
                    result = self.tools_adapter.execute_function_call_message_part(part)
                except Exception as e:
                    # Catch any exception during tool execution and return as string
                    # instead of letting it propagate to the user
                    result = str(e)
                tool_results.append(result)
        if tool_calls:
            # Prepare tool_calls message for assistant
            tool_calls_list = []
            tool_results_list = []
            for call, result in zip(tool_calls, tool_results):
                function_name = (
                    getattr(call, "name", None)
                    or (
                        getattr(call, "function", None)
                        and getattr(call.function, "name", None)
                    )
                    or "function"
                )
                arguments = getattr(call, "function", None) and getattr(
                    call.function, "arguments", None
                )
                tool_call_id = getattr(call, "tool_call_id", None)
                tool_calls_list.append(
                    {
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": function_name,
                            "arguments": (
                                arguments
                                if isinstance(arguments, str)
                                else str(arguments) if arguments else ""
                            ),
                        },
                    }
                )
                tool_results_list.append(
                    {
                        "name": function_name,
                        "content": str(result),
                        "tool_call_id": tool_call_id,
                    }
                )
            # Add assistant tool_calls message
            import json

            self.conversation_history.add_message(
                "tool_calls", json.dumps(tool_calls_list)
            )
            # Add tool_results message
            self.conversation_history.add_message(
                "tool_results", json.dumps(tool_results_list)
            )
            return True  # Continue the loop
        else:
            return False  # No tool calls, return event

    def chat(
        self,
        prompt: str = None,
        messages: Optional[List[dict]] = None,
        role: str = "user",
        config=None,
    ):
        self._clear_driver_queues()
        self._validate_and_update_history(prompt, messages, role)
        self._ensure_system_prompt()
        if config is None:
            config = self.llm_provider.driver_config
        loop_count = 1
        import threading

        # Use global cancellation manager
        from janito.llm.cancellation_manager import get_cancellation_manager

        cancel_manager = get_cancellation_manager()
        driver_cancel_event = cancel_manager.start_new_request()

        # Store cancellation event on agent for external access
        self.cancel_event = driver_cancel_event

        try:
            while True:
                self._print_verbose_chat_loop(loop_count)
                driver_input = self._prepare_driver_input(
                    config, cancel_event=driver_cancel_event
                )
                self.input_queue.put(driver_input)
                try:
                    result, added_tool_results = self._process_next_response()
                except KeyboardInterrupt:
                    cancel_manager.cancel_current_request()
                    raise
                if getattr(self, "verbose_agent", False):
                    print(
                        f"[agent] [DEBUG] Returned from _process_next_response: result={result}, added_tool_results={added_tool_results}"
                    )
                if self._should_exit_chat_loop(result, added_tool_results):
                    return result
                loop_count += 1
        finally:
            cancel_manager.clear_current_request()
            # Clean up cancellation event
            if hasattr(self, "cancel_event"):
                delattr(self, "cancel_event")

    def _clear_driver_queues(self):
        if hasattr(self, "driver") and self.driver:
            if hasattr(self.driver, "clear_output_queue"):
                self.driver.clear_output_queue()
            if hasattr(self.driver, "clear_input_queue"):
                self.driver.clear_input_queue()

    def _should_exit_chat_loop(self, result, added_tool_results):
        if result is None:
            if getattr(self, "verbose_agent", False):
                print(
                    "[agent] [INFO] Exiting chat loop: _process_next_response returned None result (likely timeout or error). Returning (None, False)."
                )
            return True
        if not added_tool_results:
            if getattr(self, "verbose_agent", False):
                print(
                    f"[agent] [INFO] Exiting chat loop: _process_next_response returned added_tool_results=False (final response or no more tool calls). Returning result: {result}"
                )
            return True
        return False

    def _print_verbose_chat_loop(self, loop_count):
        if getattr(self, "verbose_agent", False):
            print(
                f"[agent] [DEBUG] Preparing new driver_input (loop_count={loop_count}) with updated conversation history:"
            )
            for msg in self.conversation_history.get_history():
                print("   ", msg)

    def set_latest_event(self, event: str) -> None:
        with self._event_lock:
            self._latest_event = event

    def get_latest_event(self) -> Optional[str]:
        with self._event_lock:
            return self._latest_event

    def get_history(self) -> LLMConversationHistory:
        """Get the agent's interaction history."""
        return self.conversation_history

    def reset_conversation_history(self) -> None:
        """Reset/clear the interaction history."""
        self.conversation_history = LLMConversationHistory()

    def get_provider_name(self) -> str:
        """Return the provider name, if available."""
        if hasattr(self.llm_provider, "name"):
            return getattr(self.llm_provider, "name", "?")
        if self.driver and hasattr(self.driver, "name"):
            return getattr(self.driver, "name", "?")
        return "?"

    def get_model_name(self) -> str:
        """Return the model name, if available."""
        if self.driver and hasattr(self.driver, "model_name"):
            return getattr(self.driver, "model_name", "?")
        return "?"

    def get_name(self) -> Optional[str]:
        return self.agent_name

    def get_provider_name(self) -> str:
        """
        Return the provider name for this agent, if available.
        """
        if hasattr(self, "llm_provider") and hasattr(self.llm_provider, "name"):
            return self.llm_provider.name
        if (
            hasattr(self, "driver")
            and self.driver
            and hasattr(self.driver, "provider_name")
        ):
            return self.driver.provider_name
        if hasattr(self, "driver") and self.driver and hasattr(self.driver, "name"):
            return self.driver.name
        return "?"

    def get_model_name(self) -> str:
        """
        Return the model name for this agent, if available.
        """
        if (
            hasattr(self, "driver")
            and self.driver
            and hasattr(self.driver, "model_name")
        ):
            return self.driver.model_name
        if hasattr(self, "llm_provider") and hasattr(self.llm_provider, "model_name"):
            return self.llm_provider.model_name
        return "?"

    def reset_driver_config_to_model_defaults(self, model_name: str):
        """
        Reset all driver config fields to the model's defaults for the current provider (overwriting any user customizations).
        """
        provider = self.llm_provider
        model_spec = self._get_model_spec(provider, model_name)
        config = getattr(provider, "driver_config", None)
        if config is None:
            return
        self._apply_model_defaults_to_config(config, model_spec, model_name)
        self._update_driver_model_config(model_name, config)

    def _get_model_spec(self, provider, model_name):
        if hasattr(provider, "MODEL_SPECS"):
            model_spec = provider.MODEL_SPECS.get(model_name)
            if model_spec:
                return model_spec
        raise ValueError(f"Model '{model_name}' not found in provider MODEL_SPECS.")

    def _apply_model_defaults_to_config(self, config, model_spec, model_name):
        config.model = model_name
        config.temperature = self._safe_float(getattr(model_spec, "default_temp", None))
        config.max_tokens = self._safe_int(getattr(model_spec, "max_response", None))
        config.max_completion_tokens = self._safe_int(
            getattr(model_spec, "max_cot", None)
        )
        config.top_p = None
        config.presence_penalty = None
        config.frequency_penalty = None
        config.stop = None
        config.reasoning_effort = None

    def _safe_int(self, val):
        try:
            if val is None or val == "N/A":
                return None
            return int(val)
        except Exception:
            return None

    def _safe_float(self, val):
        try:
            if val is None or val == "N/A":
                return None
            return float(val)
        except Exception:
            return None

    def _update_driver_model_config(self, model_name, config):
        if self.driver is not None:
            if hasattr(self.driver, "model_name"):
                self.driver.model_name = model_name
            if hasattr(self.driver, "config"):
                self.driver.config = config

    def change_model(self, model_name: str):
        """
        Change the model for the agent's provider and driver config, and update the driver if present.
        """
        self.reset_driver_config_to_model_defaults(model_name)

    def join_driver(self, timeout=None):
        """
        Wait for the driver's background thread to finish. Call this before exiting to avoid daemon thread shutdown errors.
        :param timeout: Optional timeout in seconds.
        Handles KeyboardInterrupt gracefully.
        """
        if (
            hasattr(self, "driver")
            and self.driver
            and hasattr(self.driver, "_thread")
            and self.driver._thread
        ):
            try:
                self.driver._thread.join(timeout)
            except KeyboardInterrupt:
                print(
                    "\n[INFO] Interrupted by user during driver shutdown. Cleaning up..."
                )
                # Optionally, perform additional cleanup here
                # Do not re-raise to suppress traceback and exit gracefully
                return
