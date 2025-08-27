"""
Core PromptHandler: Handles prompt submission and response formatting for janito CLI (shared by single and chat modes).
"""

import time
from janito import __version__ as VERSION
from janito.performance_collector import PerformanceCollector
from rich.status import Status
from rich.console import Console
from typing import Any, Optional, Callable
from janito.driver_events import (
    RequestStarted,
    RequestFinished,
    RequestStatus,
    RateLimitRetry,
)
from janito.tools.tool_events import ToolCallError
import threading
from janito.cli.verbose_output import print_verbose_header
from janito.event_bus import event_bus as global_event_bus


class StatusRef:
    def __init__(self):
        self.status = None


class PromptHandler:
    args: Any
    agent: Any
    performance_collector: PerformanceCollector
    console: Console
    provider_instance: Any

    def __init__(self, args: Any, conversation_history, provider_instance) -> None:
        self.temperature = args.temperature if hasattr(args, "temperature") else None
        """
        Initialize PromptHandler.
        :param args: CLI or programmatic arguments for provider/model selection, etc.
        :param conversation_history: LLMConversationHistory object for multi-turn chat mode.
        :param provider_instance: An initialized provider instance.
        """
        self.args = args
        self.conversation_history = conversation_history
        self.provider_instance = provider_instance
        self.agent = None
        from janito.perf_singleton import performance_collector

        self.performance_collector = performance_collector
        self.console = Console()

    def _handle_inner_event(self, inner_event, on_event, status):
        if on_event:
            on_event(inner_event)
        from janito.tools.tool_events import ToolCallFinished

        if isinstance(inner_event, ToolCallFinished):
            return self._handle_tool_call_finished(inner_event)
        if isinstance(inner_event, RateLimitRetry):
            return self._handle_rate_limit_retry(inner_event, status)
        if isinstance(inner_event, RequestFinished):
            if getattr(inner_event, "status", None) == "error":
                return self._handle_request_finished_error(inner_event, status)
            if getattr(inner_event, "status", None) in (
                RequestStatus.EMPTY_RESPONSE,
                RequestStatus.TIMEOUT,
            ):
                return self._handle_empty_or_timeout(inner_event, status)
            status.update("[bold green]Received response![bold green]")
            return "break"
        if isinstance(inner_event, ToolCallError):
            return self._handle_tool_call_error(inner_event, status)
        event_type = type(inner_event).__name__
        self.console.print(
            f"[yellow]Warning: Unknown event type encountered: {event_type}[yellow]"
        )
        return None

    def _handle_tool_call_finished(self, inner_event):
        if hasattr(self.args, "verbose_tools") and self.args.verbose_tools:
            self.console.print(
                f"[cyan][tools-adapter] Tool '{inner_event.tool_name}' result:[/cyan] {inner_event.result}"
            )
        else:
            self.console.print(inner_event.result)
        return None

    def _handle_rate_limit_retry(self, inner_event, status):
        status.update(
            f"[yellow]Rate limited. Waiting {inner_event.retry_delay:.0f}s before retry (attempt {inner_event.attempt}).[yellow]"
        )
        return None

    def _handle_request_finished_error(self, inner_event, status):
        error_msg = (
            inner_event.error if hasattr(inner_event, "error") else "Unknown error"
        )
        if (
            "Status 429" in error_msg
            and "Service tier capacity exceeded for this model" in error_msg
        ):
            status.update("[yellow]Service tier capacity exceeded, retrying...[yellow]")
            return "break"
        status.update(f"[bold red]Error: {error_msg}[bold red]")
        self.console.print(f"[red]Error: {error_msg}[red]")
        return "break"

    def _handle_tool_call_error(self, inner_event, status):
        error_msg = (
            inner_event.error if hasattr(inner_event, "error") else "Unknown tool error"
        )
        tool_name = (
            inner_event.tool_name if hasattr(inner_event, "tool_name") else "unknown"
        )
        status.update(f"[bold red]Tool Error in '{tool_name}': {error_msg}[bold red]")
        self.console.print(f"[red]Tool Error in '{tool_name}': {error_msg}[red]")
        return "break"

    def _handle_empty_or_timeout(self, inner_event, status):
        details = getattr(inner_event, "details", None) or {}
        block_reason = details.get("block_reason")
        block_msg = details.get("block_reason_message")
        msg = details.get("message", "LLM returned an empty or incomplete response.")
        driver_name = getattr(inner_event, "driver_name", "unknown driver")
        if block_reason or block_msg:
            status.update(
                f"[bold yellow]Blocked by driver: {driver_name} | {block_reason or ''} {block_msg or ''}[bold yellow]"
            )
            self.console.print(
                f"[yellow]Blocked by driver: {driver_name} (empty response): {block_reason or ''}\n{block_msg or ''}[/yellow]"
            )
        else:
            status.update(
                f"[yellow]LLM produced no output for this request (driver: {driver_name}).[/yellow]"
            )
            self.console.print(
                f"[yellow]Warning: {msg} (driver: {driver_name})[/yellow]"
            )
        return "break"

    def _process_event_iter(self, event_iter, on_event):
        for event in event_iter:
            # Handle exceptions from generation thread
            if isinstance(event, dict) and event.get("type") == "exception":
                self.console.print("[red]Exception in generation thread:[red]")
                self.console.print(event.get("traceback", "No traceback available"))
                break
            if on_event:
                on_event(event)
            if isinstance(event, RequestStarted):
                pass  # No change needed for started event
            elif isinstance(event, RequestFinished) and getattr(
                event, "status", None
            ) in ("error", "cancelled"):
                # Handle error/cancelled as needed
                for inner_event in event_iter:
                    result = self._handle_inner_event(inner_event, on_event, None)
                    if result == "break":
                        break
                # After exiting, continue with next events (if any)
            # Handle other event types outside the spinner if needed
            elif isinstance(event, RequestFinished) and getattr(
                event, "status", None
            ) in (RequestStatus.EMPTY_RESPONSE, RequestStatus.TIMEOUT):
                details = getattr(event, "details", None) or {}
                block_reason = details.get("block_reason")
                block_msg = details.get("block_reason_message")
                msg = details.get(
                    "message", "LLM returned an empty or incomplete response."
                )
                driver_name = getattr(event, "driver_name", "unknown driver")
                if block_reason or block_msg:
                    self.console.print(
                        f"[yellow]Blocked by driver: {driver_name} (empty response): {block_reason or ''}\n{block_msg or ''}[/yellow]"
                    )
                else:
                    self.console.print(
                        f"[yellow]Warning: {msg} (driver: {driver_name})[/yellow]"
                    )
            else:
                pass

    def handle_prompt(
        self, user_prompt, args=None, print_header=True, raw=False, on_event=None
    ):
        # args defaults to self.args for compatibility in interactive mode
        args = (
            args if args is not None else self.args if hasattr(self, "args") else None
        )
        # Join/cleanup prompt
        if isinstance(user_prompt, list):
            user_prompt = " ".join(user_prompt).strip()
        else:
            user_prompt = str(user_prompt).strip() if user_prompt is not None else ""
        if not user_prompt:
            raise ValueError("No user prompt was provided!")
        if print_header and hasattr(self, "agent") and args is not None:
            print_verbose_header(self.agent, args)
        self.run_prompt(user_prompt, raw=raw, on_event=on_event)

    def run_prompt(
        self, user_prompt: str, raw: bool = False, on_event: Optional[Callable] = None
    ) -> None:
        """
        Handles a single prompt, using the blocking event-driven chat interface.
        Optionally takes an on_event callback for custom event handling.
        """
        try:
            self._print_verbose_debug("Calling agent.chat()...")

            # Use global cancellation manager
            from janito.llm.cancellation_manager import get_cancellation_manager
            import time
            from threading import Thread, Event

            cancel_manager = get_cancellation_manager()
            driver_cancel_event = cancel_manager.start_new_request()

            # Timer setup with live status display
            start_time = time.time()
            stop_timer = Event()
            
            # Create a status display with timer
            from rich.live import Live
            from rich.text import Text
            
            def get_timer_text():
                elapsed = time.time() - start_time
                minutes, seconds = divmod(int(elapsed), 60)
                return Text(f"⏱️  Waiting for response... {minutes:02d}:{seconds:02d}", style="cyan")
            
            # Use Live display for updating timer
            with Live(get_timer_text(), refresh_per_second=4, console=self.console) as live:
                def update_timer():
                    while not stop_timer.wait(0.25):  # Update every 250ms
                        live.update(get_timer_text())
                
                timer_thread = Thread(target=update_timer, daemon=True)
                timer_thread.start()

                try:
                    final_event = self.agent.chat(prompt=user_prompt)
                    stop_timer.set()  # Stop the timer
                    
                    if hasattr(self.agent, "set_latest_event"):
                        self.agent.set_latest_event(final_event)
                    self.agent.last_event = final_event
                    self._print_verbose_debug(f"agent.chat() returned: {final_event}")
                    self._print_verbose_final_event(final_event)
                    if on_event and final_event is not None:
                        on_event(final_event)
                        global_event_bus.publish(final_event)
                finally:
                    stop_timer.set()  # Ensure timer stops
                    cancel_manager.clear_current_request()

        except KeyboardInterrupt:
            # Capture user interrupt / cancellation
            self.console.print("[red]Interrupted by the user.[/red]")
            try:
                from janito.driver_events import RequestFinished, RequestStatus

                # Record a synthetic "cancelled" final event so that downstream
                # handlers (e.g. single_shot_mode.handler._post_prompt_actions)
                # can reliably detect that the prompt was interrupted by the
                # user and avoid showing misleading messages such as
                # "No output produced by the model.".
                if hasattr(self, "agent") and self.agent is not None:
                    self.agent.last_event = RequestFinished(
                        status=RequestStatus.CANCELLED,
                        reason="Interrupted by the user",
                    )
            except Exception:
                # Do not fail on cleanup – this hook is best-effort only.
                pass

    def _print_verbose_debug(self, message):
        if hasattr(self.args, "verbose_agent") and self.args.verbose_agent:
            print(f"[prompt_core][DEBUG] {message}")

    def _print_verbose_final_event(self, final_event):
        if hasattr(self.args, "verbose_agent") and self.args.verbose_agent:
            print("[prompt_core][DEBUG] Received final_event from agent.chat:")
            print(f"  [prompt_core][DEBUG] type={type(final_event)}")
            print(f"  [prompt_core][DEBUG] content={final_event}")

    def run_prompts(
        self, prompts: list, raw: bool = False, on_event: Optional[Callable] = None
    ) -> None:
        """
        Handles multiple prompts in sequence, collecting performance data for each.
        """
        for prompt in prompts:
            self.run_prompt(prompt, raw=raw, on_event=on_event)
        # No return value
