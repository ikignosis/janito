"""Web server runtime configuration built from CLI args."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class WebServerConfig:
    """Runtime configuration for the web server, built from CLI args.

    Mirrors the logic in ``cli/chat.py::run_interactive_chat()`` for choosing
    system prompts and enabling toolsets.
    """

    # --- Server binding ---
    host: str = "127.0.0.1"
    port: int = 8080
    open_browser: bool = True

    # --- AI / provider (already resolved into env vars by cli/setup.py) ---
    # These are read from env for display/status, but kept for /api/config.
    provider: Optional[str] = None       # args.provider
    model: Optional[str] = None          # args.model (or from env)
    endpoint: Optional[str] = None       # args.endpoint

    # --- Session defaults (from CLI flags) ---
    thinking: bool = False               # -t / --thinking
    verbose: bool = False                # -v / --verbose
    no_history: bool = False             # --no-history

    # --- Toolset enablement ---
    gmail: bool = False                  # --gmail
    onedrive: bool = False               # --onedrive

    # --- System prompt ---
    system_prompt: Optional[str] = None  # -S "custom prompt"
    no_system_prompt: bool = False       # -Z
    no_tools: bool = False               # implied by -Z or -S

    # --- Security ---
    auth_token: Optional[str] = None     # from JANITO_WEB_TOKEN env

    # --- The original CLI args (for /api/config/cli display) ---
    cli_args: Optional[dict] = None

    @classmethod
    def from_args(cls, args) -> "WebServerConfig":
        """Build config from parsed argparse.Namespace."""
        config = cls(
            host=getattr(args, "host", "127.0.0.1"),
            port=getattr(args, "port", 8080),
            open_browser=not getattr(args, "no_open", False),
            provider=getattr(args, "provider", None),
            model=getattr(args, "model", None) or os.getenv("OPENAI_MODEL"),
            endpoint=getattr(args, "endpoint", None),
            thinking=getattr(args, "thinking", False),
            verbose=getattr(args, "verbose", False),
            no_history=getattr(args, "no_history", False),
            gmail=getattr(args, "gmail", False),
            onedrive=getattr(args, "onedrive", False),
            auth_token=os.getenv("JANITO_WEB_TOKEN"),
        )

        # Capture a subset of CLI args for the /api/config/cli endpoint
        config.cli_args = {
            k: getattr(args, k, None)
            for k in ("provider", "model", "endpoint", "thinking", "verbose",
                      "no_history", "gmail", "onedrive", "read", "write", "exec",
                      "system_prompt", "no_system_prompt", "log", "host", "port",
                      "no_open", "web")
        }

        # System prompt resolution (mirrors cli/chat.py logic)
        if getattr(args, "system_prompt", None):
            config.system_prompt = args.system_prompt
            config.no_tools = True
        elif getattr(args, "no_system_prompt", False):
            config.no_system_prompt = True
            config.no_tools = True
        # else: default prompt resolved at session creation time

        return config

    def get_effective_system_prompt(self) -> Optional[str]:
        """Resolve the system prompt for new sessions.

        Mirrors the if/elif chain in ``cli/chat.py::run_interactive_chat()``.
        """
        if self.system_prompt:
            return self.system_prompt
        if self.no_system_prompt:
            return None
        if self.onedrive:
            from janito.tools.onedrive import ONEDRIVE_SYSTEM_PROMPT
            return ONEDRIVE_SYSTEM_PROMPT
        if self.gmail:
            from janito.tools.gmail import GMAIL_SYSTEM_PROMPT
            return GMAIL_SYSTEM_PROMPT
        from janito.system_prompt import get_system_prompt_with_skills
        return get_system_prompt_with_skills()

    def apply_toolsets(self) -> None:
        """Enable toolsets based on CLI flags (gmail, onedrive).

        Mirrors the setup block in ``cli/chat.py::run_interactive_chat()``.
        Called once at server startup.
        """
        from janito.tooling.tools_registry import add_toolset
        if self.gmail:
            add_toolset("gmail")
        if self.onedrive:
            add_toolset("onedrive")
