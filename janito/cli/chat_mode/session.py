"""
Session management for Janito Chat CLI.
Defines ChatSession and ChatShellState classes.
"""

from __future__ import annotations

import types
from rich.console import Console
from rich.rule import Rule
from prompt_toolkit.history import InMemoryHistory
from janito.cli.chat_mode.shell.input_history import UserInputHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit import PromptSession
from janito.cli.chat_mode.toolbar import get_toolbar_func
from prompt_toolkit.enums import EditingMode
from janito.cli.chat_mode.prompt_style import chat_shell_style
from janito.cli.chat_mode.bindings import KeyBindingsFactory
from janito.cli.chat_mode.shell.commands import handle_command
from janito.cli.chat_mode.shell.autocomplete import ShellCommandCompleter
import time

# Shared prompt/agent factory
from janito.cli.prompt_setup import setup_agent_and_prompt_handler

import time


class ChatShellState:
    def __init__(self, mem_history, conversation_history):
        self.mem_history = mem_history
        self.conversation_history = conversation_history
        self.paste_mode = False

        self._pid = None
        self._stdout_path = None
        self._stderr_path = None

        self._status = (
            "starting"  # Tracks the current  status (updated by background thread/UI)
        )

        self.last_usage_info = {}
        self.last_elapsed = None
        self.main_agent = {}
        self.mode = None
        self.agent = None
        self.main_agent = None
        self.main_enabled = False
        self.no_tools_mode = False


class ChatSession:
    def __init__(
        self,
        console,
        provider_instance=None,
        llm_driver_config=None,
        role=None,
        args=None,
        verbose_tools=False,
        verbose_agent=False,
        allowed_permissions=None,
    ):
        self.console = console
        self.user_input_history = UserInputHistory()
        self.input_dicts = self.user_input_history.load()
        self.mem_history = InMemoryHistory()
        for item in self.input_dicts:
            if isinstance(item, dict) and "input" in item:
                self.mem_history.append_string(item["input"])
        self.provider_instance = provider_instance
        self.llm_driver_config = llm_driver_config

        profile, role, profile_system_prompt, no_tools_mode = (
            self._select_profile_and_role(args, role)
        )
        # Propagate no_tools_mode flag to downstream components via args
        if args is not None and not hasattr(args, "no_tools_mode"):
            try:
                setattr(args, "no_tools_mode", no_tools_mode)
            except Exception:
                pass
        conversation_history = self._create_conversation_history()
        self.agent, self._prompt_handler = self._setup_agent_and_prompt_handler(
            args,
            provider_instance,
            llm_driver_config,
            role,
            verbose_tools,
            verbose_agent,
            allowed_permissions,
            profile,
            profile_system_prompt,
            conversation_history,
        )
        self.profile = profile  # Store profile name for welcome message
        self.shell_state = ChatShellState(self.mem_history, conversation_history)
        self.shell_state.agent = self.agent
        # Set no_tools_mode if present
        self.shell_state.no_tools_mode = bool(no_tools_mode)
        self._filter_execution_tools()
        from janito.perf_singleton import performance_collector

        self.performance_collector = performance_collector
        self.key_bindings = KeyBindingsFactory.create()
        self._prompt_handler.agent = self.agent
        self._prompt_handler.conversation_history = (
            self.shell_state.conversation_history
        )
        self._support = False

        # Check if multi-line mode should be enabled by default
        self.multi_line_mode = getattr(args, "multi", False) if args else False

    def _select_profile_and_role(self, args, role):
        profile = getattr(args, "profile", None) if args is not None else None
        role_arg = getattr(args, "role", None) if args is not None else None
        python_profile = (
            getattr(args, "developer", False) if args is not None else False
        )
        market_profile = getattr(args, "market", False) if args is not None else False
        profile_system_prompt = None
        no_tools_mode = False

        # Handle --developer flag
        if python_profile and profile is None and role_arg is None:
            profile = "Developer with Python Tools"

        # Handle --market flag
        if market_profile and profile is None and role_arg is None:
            profile = "Market Analyst"

        if (
            profile is None
            and role_arg is None
            and not python_profile
            and not market_profile
        ):
            # Skip interactive profile selection for list commands
            from janito.cli.core.getters import GETTER_KEYS

            # Check if any getter command is active - these don't need interactive mode
            skip_profile_selection = False
            if args is not None:
                for key in GETTER_KEYS:
                    if getattr(args, key, False):
                        skip_profile_selection = True
                        break

            if skip_profile_selection:
                profile = "Developer with Python Tools"  # Default for non-interactive commands
            else:
                try:
                    from janito.cli.chat_mode.session_profile_select import (
                        select_profile,
                    )

                    result = select_profile()
                    if isinstance(result, dict):
                        profile = result.get("profile")
                        profile_system_prompt = result.get("profile_system_prompt")
                        no_tools_mode = result.get("no_tools_mode", False)
                    elif isinstance(result, str) and result.startswith("role:"):
                        role = result[len("role:") :].strip()
                        profile = "Developer with Python Tools"
                    else:
                        profile = (
                            "Developer with Python Tools"
                            if result == "Developer"
                            else result
                        )
                except ImportError:
                    profile = "Raw Model Session (no tools, no context)"
        if role_arg is not None:
            role = role_arg
            if profile is None:
                profile = "Developer with Python Tools"
        return profile, role, profile_system_prompt, no_tools_mode

    def _create_conversation_history(self):
        from janito.conversation_history import LLMConversationHistory

        return LLMConversationHistory()

    def _setup_agent_and_prompt_handler(
        self,
        args,
        provider_instance,
        llm_driver_config,
        role,
        verbose_tools,
        verbose_agent,
        allowed_permissions,
        profile,
        profile_system_prompt,
        conversation_history,
    ):
        return setup_agent_and_prompt_handler(
            args=args,
            provider_instance=provider_instance,
            llm_driver_config=llm_driver_config,
            role=role,
            verbose_tools=verbose_tools,
            verbose_agent=verbose_agent,
            allowed_permissions=allowed_permissions,
            profile=profile,
            profile_system_prompt=profile_system_prompt,
            conversation_history=conversation_history,
        )

    def _filter_execution_tools(self):
        try:
            getattr(
                __import__("janito.tools", fromlist=["get_local_tools_adapter"]),
                "get_local_tools_adapter",
            )()
        except Exception as e:
            self.console.print(
                f"[yellow]Warning: Could not filter execution tools at startup: {e}[/yellow]"
            )

            _thread = _start_and_watch(self.shell_state, self._lock, get__port())
            self._thread = _thread
        else:
            self.shell_state._support = False
            self.shell_state._status = "offline"

    def run(self):
        self.console.clear()
        from janito import __version__

        self.console.print(f"[bold green]Janito Chat Mode v{__version__}[/bold green]")
        self.console.print(f"[dim]Profile: {self.profile}[/dim]")

        import os

        cwd = os.getcwd()
        home = os.path.expanduser("~")
        if cwd.startswith(home):
            cwd_display = "~" + cwd[len(home) :]
        else:
            cwd_display = cwd
        from janito.cli.chat_mode.shell.commands._priv_status import (
            get_privilege_status_message,
        )

        priv_status = get_privilege_status_message()
        self.console.print(
            f"[green]Working Dir:[/green] [cyan]{cwd_display}[/cyan]  |  {priv_status}"
        )

        if self.multi_line_mode:
            self.console.print(
                "[blue]Multi-line input mode enabled (Esc+Enter or Ctrl+D to submit)[/blue]"
            )

        from janito.cli.chat_mode.shell.commands._priv_check import (
            user_has_any_privileges,
        )

        perms = __import__(
            "janito.tools.permissions", fromlist=["get_global_allowed_permissions"]
        ).get_global_allowed_permissions()
        if perms.execute:
            self.console.print(
                "[bold red]Commands/Code execution is enabled -  Be cautious[/bold red]"
            )
        if not (perms.read or perms.write or perms.execute):
            self.console.print(
                "[yellow]Note: You currently have no privileges enabled. If you need to interact with files or the system, enable permissions using /read on, /write on, or /execute on.[/yellow]"
            )

        session = self._create_prompt_session()
        self._chat_loop(session)

    def _chat_loop(self, session):
        self.msg_count = 0
        timer_started = False
        while True:
            if not timer_started:
                timer_started = True
            cmd_input = self._handle_input(session)
            if cmd_input is None:
                break
            if not cmd_input:
                continue
            if self._handle_exit_conditions(cmd_input):
                break
            if self._handle_command_input(cmd_input):
                continue
            self.user_input_history.append(cmd_input)
            self._process_prompt(cmd_input)

    def _handle_command_input(self, cmd_input):
        if cmd_input.startswith("/"):
            handle_command(cmd_input, shell_state=self.shell_state)
            return True
        if cmd_input.startswith("!"):
            handle_command(f"! {cmd_input[1:]}", shell_state=self.shell_state)
            return True
        return False

    def _process_prompt(self, cmd_input):
        try:
            # Clear screen before processing new prompt
            self.console.clear()
            import time

            final_event = (
                self._prompt_handler.agent.last_event
                if hasattr(self._prompt_handler.agent, "last_event")
                else None
            )
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

            backend_hostname = "Unknown"
            candidates = []
            drv = getattr(self.agent, "driver", None)
            if drv is not None:
                cfg = getattr(drv, "config", None)
                if cfg is not None:
                    b = getattr(cfg, "base_url", None)
                    if b:
                        candidates.append(b)
                direct_base = getattr(drv, "base_url", None)
                if direct_base:
                    candidates.append(direct_base)
            cfg2 = getattr(self.agent, "config", None)
            if cfg2 is not None:
                b2 = getattr(cfg2, "base_url", None)
                if b2:
                    candidates.append(b2)
            top_base = getattr(self.agent, "base_url", None)
            if top_base:
                candidates.append(top_base)
            from urllib.parse import urlparse

            for candidate in candidates:
                try:
                    if not candidate:
                        continue
                    parsed = urlparse(str(candidate))
                    host = parsed.netloc or parsed.path
                    if host:
                        backend_hostname = host
                        break
                except Exception:
                    backend_hostname = str(candidate)
                    break

            self.console.print(
                Rule(
                    f"[bold blue]Model: {model_name} ({provider_name}) | Backend: {backend_hostname}[/bold blue]"
                )
            )

            self._prompt_handler.run_prompt(cmd_input)
            end_time = time.time()
            elapsed = end_time - start_time
            self.msg_count += 1
            from janito.formatting_token import print_token_message_summary

            usage = self.performance_collector.get_last_request_usage()
            print_token_message_summary(
                self.console, self.msg_count, usage, elapsed=elapsed
            )
            # Send terminal bell character to trigger TUI bell after printing token summary
            print("\a", end="", flush=True)
            if final_event and hasattr(final_event, "metadata"):
                exit_reason = (
                    final_event.metadata.get("exit_reason")
                    if hasattr(final_event, "metadata")
                    else None
                )
                if exit_reason:
                    self.console.print(
                        f"[bold yellow]Exit reason: {exit_reason}[/bold yellow]"
                    )
        except Exception as exc:
            self.console.print(f"[red]Exception in agent: {exc}[/red]")
            import traceback

            self.console.print(traceback.format_exc())

    def _create_prompt_session(self):
        return PromptSession(
            style=chat_shell_style,
            completer=ShellCommandCompleter(),
            history=self.mem_history,
            editing_mode=EditingMode.EMACS,
            key_bindings=self.key_bindings,
            bottom_toolbar=lambda: get_toolbar_func(
                self.performance_collector, 0, self.shell_state
            )(),
            multiline=self.multi_line_mode,
        )

    def _handle_input(self, session):
        injected = getattr(self.shell_state, "injected_input", None)
        if injected is not None:
            cmd_input = injected
            self.shell_state.injected_input = None
        else:
            try:
                cmd_input = session.prompt(HTML("<inputline>💬 </inputline>"))
            except (KeyboardInterrupt, EOFError):
                self._handle_exit()
                return None
        sanitized = cmd_input.strip()
        try:
            sanitized.encode("utf-8")
        except UnicodeEncodeError:
            sanitized = sanitized.encode("utf-8", errors="replace").decode("utf-8")
            self.console.print(
                "[yellow]Warning: Some characters in your input were not valid UTF-8 and have been replaced.[/yellow]"
            )
        return sanitized

    def _handle_exit(self):
        self.console.print("[bold yellow]Exiting chat. Goodbye![/bold yellow]")
        if hasattr(self, "agent") and hasattr(self.agent, "join_driver"):
            if (
                hasattr(self.agent, "input_queue")
                and self.agent.input_queue is not None
            ):
                self.agent.input_queue.put(None)
            self.agent.join_driver()

    def _handle_exit_conditions(self, cmd_input):
        if cmd_input.lower() in ("/exit", ":q", ":quit"):
            self._handle_exit()
            return True
        return False
