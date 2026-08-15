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
        from janito.config_loaders import load_model_from_config

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
    # args.api_type -- overrides the provider's configured api-type for the
    # whole server run (like the CLI chat modes).  ``None`` = follow the
    # provider's configured api-type (the web Settings drawer's per-provider
    # combo, written to config.json) or its built-in default.
    api_type: str | None = None

    # Session-only provider override set from the chat-page topbar combo.
    # Unlike ``provider`` (which mirrors the persisted default), this is
    # never written to ``~/.janito/config.json``: it only affects this
    # running server and is lost on restart.  ``None`` means "no override"
    # (fall back to the persisted/default provider).
    session_provider: str | None = None

    # --- Session defaults (from CLI flags) ---
    thinking: bool = False  # -t / --thinking
    verbose: bool = False  # -v / --verbose
    no_history: bool = False  # --no-history

    # Runtime thinking override set from the status-bar toggle (POST
    # /api/config/thinking). In-memory only — never written to
    # ~/.janito/config.json and lost on restart (like session_provider).
    # ``None`` = no override (follow the CLI flag, else the provider default).
    thinking_override: bool | None = None

    @property
    def effective_thinking(self) -> bool:
        """Whether thinking mode is active for the next prompt.

        Resolution order: the runtime ``thinking_override`` (status-bar
        toggle) first, then the explicit ``--thinking`` CLI flag, then the
        effective provider's built-in ``thinking`` resolved for the
        **effective model** (``self.model``: the CLI ``--model``, else the
        provider's configured model, else its built-in default model) --
        True for DeepSeek and Alibaba/Qwen, whose models reason by default.
        The effective provider is the session-only combo override, else the
        CLI ``--provider``, else the persisted default.
        """
        if self.thinking_override is not None:
            return self.thinking_override
        if self.thinking:
            return True
        from janito.general_config import get_active_provider
        from janito.provider_accessors import get_default_thinking_from_provider

        provider = self.session_provider or self.provider or get_active_provider()
        return bool(get_default_thinking_from_provider(provider, self.model))

    # --- Toolset enablement ---
    gmail: bool = False  # --gmail
    onedrive: bool = False  # --onedrive

    # --- System prompt ---
    system_prompt: str | None = None  # -S "custom prompt"
    no_system_prompt: bool = False  # -Z
    no_tools: bool = False  # implied by -Z

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
            api_type=getattr(args, "api_type", None),
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
                "api_type",
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
                "no_tools",
                "log",
                "web_host",
                "web_port",
                "no_web_open",
                "web",
            )
        }

        # --no-tools: stop loading non-skill tools (skill tools stay enabled).
        # The registry is module-global, so applying it here keeps direct
        # WebServerConfig.from_args(...) constructions consistent with the
        # CLI path (__main__._setup_runtime already applied it before the
        # server starts).
        if getattr(args, "no_tools", False):
            from janito.tooling.tools_registry import disable_tools_loading

            disable_tools_loading()

        # System prompt resolution (mirrors cli/chat.py logic)
        if getattr(args, "system_prompt", None):
            config.system_prompt = args.system_prompt
        elif getattr(args, "no_system_prompt", False):
            config.no_system_prompt = True
            config.no_tools = True
        # else: default prompt resolved at session creation time

        return config

    def get_effective_system_prompt(self) -> str | None:
        """Resolve the system prompt for new sessions.

        Shared with ``cli/chat.py`` via :class:`janito.cli.session_setup.SessionSetup`.
        """
        from janito.cli.session_setup import SessionSetup

        return SessionSetup(
            system_prompt=self.system_prompt,
            no_system_prompt=self.no_system_prompt,
            gmail=self.gmail,
            onedrive=self.onedrive,
        ).effective_system_prompt()

    def apply_toolsets(self) -> None:
        """Enable toolsets based on CLI flags (gmail, onedrive).

        Shared with ``cli/chat.py`` via :class:`janito.cli.session_setup.SessionSetup`.
        Called once at server startup.
        """
        from janito.cli.session_setup import SessionSetup

        # The janitoweb toolset (CreateSVG, ...) is web-only and always
        # loaded when the server runs in --web mode.  See issue #11.
        SessionSetup(gmail=self.gmail, onedrive=self.onedrive).enable_toolsets(
            extra=["janitoweb"]
        )
