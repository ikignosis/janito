"""
PromptHandler: Handles prompt submission and response formatting for janito CLI (one-shot prompt execution).
"""

from __future__ import annotations

from janito.cli.prompt_setup import setup_agent_and_prompt_handler
import janito.tools  # Ensure all tools are registered
from janito.cli.console import shared_console
import time


class PromptHandler:
    def __init__(
        self,
        args,
        provider_instance,
        llm_driver_config,
        role=None,
        allowed_permissions=None,
    ):
        self.args = args
        self.provider_instance = provider_instance
        self.llm_driver_config = llm_driver_config
        self.role = role
        # Instantiate agent together with prompt handler using the shared helper
        # Handle --developer and --market flags for single shot mode
        profile = getattr(args, "profile", None)
        if profile is None and getattr(args, "developer", False):
            profile = "Developer with Python Tools"
        if profile is None and getattr(args, "market", False):
            profile = "Market Analyst"

        self.agent, self.generic_handler = setup_agent_and_prompt_handler(
            args=args,
            provider_instance=provider_instance,
            llm_driver_config=llm_driver_config,
            role=role,
            verbose_tools=getattr(args, "verbose_tools", False),
            verbose_agent=getattr(args, "verbose_agent", False),
            allowed_permissions=allowed_permissions,
            profile=profile,
        )

    def handle(self) -> None:
        import traceback

        user_prompt = " ".join(getattr(self.args, "user_prompt", [])).strip()
        # UTF-8 sanitize user_prompt
        sanitized = user_prompt
        try:
            sanitized.encode("utf-8")
        except UnicodeEncodeError:
            sanitized = sanitized.encode("utf-8", errors="replace").decode("utf-8")
            shared_console.print(
                "[yellow]Warning: Some characters in your input were not valid UTF-8 and have been replaced.[/yellow]"
            )
        import time

        try:
            start_time = time.time()

            # Print rule line with model info before processing prompt
            model_name = (
                self.agent.get_model_name()
                if hasattr(self.agent, "get_model_name")
                else "Unknown"
            )
            provider_name = (
                self.agent.get_provider_name()
                if hasattr(self.agent, "get_provider_name")
                else "Unknown"
            )

            # Get backend hostname if available
            backend_hostname = "Unknown"
            if hasattr(self.agent, "driver") and self.agent.driver:
                if hasattr(self.agent.driver, "config") and hasattr(
                    self.agent.driver.config, "base_url"
                ):
                    base_url = self.agent.driver.config.base_url
                    if base_url:
                        try:
                            from urllib.parse import urlparse

                            parsed = urlparse(base_url)
                            backend_hostname = parsed.netloc
                        except Exception:
                            backend_hostname = base_url

            from rich.rule import Rule

            shared_console.print(
                Rule(
                    f"[bold blue]Model: {model_name} ({provider_name}) | Backend: {backend_hostname}[/bold blue]"
                )
            )

            self.generic_handler.handle_prompt(
                sanitized,
                args=self.args,
                print_header=True,
                raw=getattr(self.args, "raw", False),
            )
            end_time = time.time()
            elapsed = end_time - start_time
            self._post_prompt_actions(elapsed=elapsed)
            if hasattr(self.args, "verbose_agent") and self.args.verbose_agent:
                print("[debug] handle_prompt() completed without exception.")
        except Exception as e:
            print(
                f"[error] Exception occurred in handle_prompt: {type(e).__name__}: {e}"
            )
            traceback.print_exc()

    def _post_prompt_actions(self, elapsed=None):
        # Align with chat mode: only print token usage summary
        import sys
        from janito.formatting_token import print_token_message_summary
        from janito.perf_singleton import performance_collector

        usage = performance_collector.get_last_request_usage()
        # If running in stdin mode, do not print token usage
        if sys.stdin.isatty():
            print_token_message_summary(
                shared_console, msg_count=1, usage=usage, elapsed=elapsed
            )
        self._cleanup_driver_and_console()

    def _cleanup_driver_and_console(self):
        if hasattr(self.agent, "join_driver"):
            if (
                hasattr(self.agent, "input_queue")
                and self.agent.input_queue is not None
            ):
                self.agent.input_queue.put(None)
            self.agent.join_driver()
        try:
            shared_console.file.flush()
        except Exception:
            pass
        try:
            import sys

            sys.stdout.flush()
        except Exception:
            pass
        # If event logger is active, flush event log
