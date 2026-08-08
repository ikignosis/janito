"""
System-prompt and toolset selection shared by the CLI and web modes.

The same "which system prompt applies?" decision (custom ``-S`` prompt, ``-Z``
no-prompt, OneDrive mode, Gmail mode, or the default skills-advertising
prompt) and the same "which toolsets to enable?" decision (gmail, onedrive)
were previously implemented twice: in ``janito/cli/chat.py``
(``_resolve_system_prompt`` / ``_build_single_prompt_context`` /
``_enable_requested_toolsets``) and in
``janito/web/backend/config.py`` (``WebServerConfig.get_effective_system_prompt``
/ ``apply_toolsets``).  :class:`SessionSetup` centralizes them so both entry
points stay in sync; the CLI/web functions delegate to it.
"""

from __future__ import annotations


class SessionSetup:
    """Resolve the effective system prompt and the toolsets for a session.

    Args:
        system_prompt: A custom system prompt (``-S``). When set, it wins over
            every other mode and implies ``no_tools``.
        no_system_prompt: ``-Z``: send no system prompt at all (implies
            ``no_tools``).
        gmail: ``--gmail``: use the Gmail-specific system prompt and enable
            the Gmail tools.
        onedrive: ``--onedrive``: use the OneDrive-specific system prompt and
            enable the OneDrive tools.
    """

    def __init__(
        self,
        *,
        system_prompt: str | None = None,
        no_system_prompt: bool = False,
        gmail: bool = False,
        onedrive: bool = False,
    ) -> None:
        self.system_prompt = system_prompt
        self.no_system_prompt = no_system_prompt
        self.gmail = gmail
        self.onedrive = onedrive

    @property
    def no_tools(self) -> bool:
        """Whether tools must be suppressed for this session.

        A custom ``-S`` prompt or ``-Z`` implies no tools; the default and the
        Gmail/OneDrive modes pass tools (``None`` = use all available).
        """
        return bool(self.system_prompt or self.no_system_prompt)

    def effective_system_prompt(self) -> str | None:
        """Resolve the system prompt for the enabled modes.

        Mirrors the if/elif chain previously duplicated between ``cli/chat.py``
        and ``WebServerConfig``:

        - a custom ``system_prompt`` wins;
        - ``no_system_prompt`` yields ``None``;
        - OneDrive mode uses the OneDrive prompt;
        - Gmail mode uses the Gmail prompt;
        - otherwise the default skills-advertising prompt applies.

        Returns:
            The effective system prompt, or ``None`` when none is used.
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

    def messages_context(self) -> list[dict]:
        """Build the seeded ``messages`` history for a single-prompt run.

        Returns:
            ``[{"role": "system", "content": <prompt>}]`` when a system prompt
            applies, otherwise ``[]``.
        """
        prompt = self.effective_system_prompt()
        if prompt:
            return [{"role": "system", "content": prompt}]
        return []

    def tools_arg(self) -> list | None:
        """Build the ``tools`` argument for a single-prompt run.

        Returns:
            ``[]`` when tools must be suppressed (custom ``-S`` / ``-Z``),
            otherwise ``None`` (the caller uses all available tools).
        """
        return [] if self.no_tools else None

    def enable_toolsets(self, *, extra: list[str] | None = None) -> None:
        """Enable the Gmail/OneDrive toolsets (and any extras) when requested.

        Args:
            extra: Additional toolset names to enable unconditionally (e.g.
                the web-only ``"janitoweb"`` toolset).
        """
        from janito.tooling.tools_registry import add_toolset

        for name in extra or []:
            add_toolset(name)
        if self.gmail:
            add_toolset("gmail")
        if self.onedrive:
            add_toolset("onedrive")
