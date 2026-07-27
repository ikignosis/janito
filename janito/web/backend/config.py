"""Web server runtime configuration built from CLI args."""

import os
from dataclasses import dataclass


def _resolve_model_from_config(provider: str | None) -> str | None:
    """Resolve the model from the config file for the given/active provider.

    Mirrors the runtime resolution used by the CLI: the model is ``--model``
    or, failing that, the provider's configured model (``<provider>.model``) in
    ``~/.janito/config.json``. No ``OPENAI_*`` environment variables are used.
    """
    try:
        from janito.general_config import load_model_from_config

        return load_model_from_config(provider)
    except Exception:
        return None


@dataclass
class WebServerConfig:
    """Runtime configuration for the web server, built from CLI args.

    Mirrors the logic in ``cli/chat.py::run_interactive_chat()`` for choosing
    system prompts and enabling toolsets.
    """

    # --- Server binding ---
    web_host: str = "127.0.0.1"
    web_port: int = 8080
    no_web_open: bool = False

    # --- AI / provider (resolved from auth store + config file) ---
    provider: str | None = None  # args.provider
    model: str | None = None  # args.model (or from provider config)

    # --- Session defaults (from CLI flags) ---
    thinking: bool = False  # -t / --thinking
    verbose: bool = False  # -v / --verbose
    no_history: bool = False  # --no-history

    # --- Toolset enablement ---
    gmail: bool = False  # --gmail
    onedrive: bool = False  # --onedrive

    # --- System prompt ---
    system_prompt: str | None = None  # -S "custom prompt"
    no_system_prompt: bool = False  # -Z
    no_tools: bool = False  # implied by -Z or -S

    # --- Security ---
    auth_token: str | None = None  # from JANITO_WEB_TOKEN env

    # --- The original CLI args (for /api/config/cli display) ---
    cli_args: dict | None = None

    @classmethod
    def from_args(cls, args) -> "WebServerConfig":
        """Build config from parsed argparse.Namespace."""
        config = cls(
            web_host=getattr(args, "web_host", "127.0.0.1"),
            web_port=getattr(args, "web_port", 8080),
            no_web_open=getattr(args, "no_web_open", False),
            provider=getattr(args, "provider", None),
            model=getattr(args, "model", None)
            or _resolve_model_from_config(getattr(args, "provider", None)),
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
            for k in (
                "provider",
                "model",
                "thinking",
                "verbose",
                "no_history",
                "gmail",
                "onedrive",
                "read",
                "write",
                "exec",
                "system_prompt",
                "no_system_prompt",
                "log",
                "web_host",
                "web_port",
                "no_web_open",
                "web",
            )
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

    def get_effective_system_prompt(self) -> str | None:
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

        # The janitoweb toolset (CreateSVG, …) is web-only and always
        # loaded when the server runs in --web mode.  See issue #11.
        add_toolset("janitoweb")

        if self.gmail:
            add_toolset("gmail")
        if self.onedrive:
            add_toolset("onedrive")
