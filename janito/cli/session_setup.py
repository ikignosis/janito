"""
System-prompt and toolset selection shared by the CLI and web modes.

The same "which system prompt applies?" decision (custom ``-S`` prompt, ``-Z``
no-prompt, or the default skills-advertising prompt) was previously
implemented twice: in ``janito/cli/chat.py`` (``_resolve_system_prompt`` /
``_build_single_prompt_context``) and in
``janito/web/backend/config.py`` (``WebServerConfig.get_effective_system_prompt``).
:class:`SessionSetup` centralizes them so both entry points stay in sync;
the CLI/web functions delegate to it.
"""

from __future__ import annotations


class SessionSetup:
    """Resolve the effective system prompt for a session.

    Args:
        system_prompt: A custom system prompt (``-S``). When set, it wins over
            every other mode; tools stay enabled.
        no_system_prompt: ``-Z``: send no system prompt at all (implies
            ``no_tools``).
    """

    def __init__(
        self,
        *,
        system_prompt: str | None = None,
        no_system_prompt: bool = False,
    ) -> None:
        self.system_prompt = system_prompt
        self.no_system_prompt = no_system_prompt

    @property
    def no_tools(self) -> bool:
        """Whether tools must be suppressed for this session.

        Only ``-Z`` (no system prompt) suppresses tools; a custom ``-S``
        prompt and the default pass tools (``None`` = use all available).
        """
        return bool(self.no_system_prompt)

    def effective_system_prompt(self) -> str | None:
        """Resolve the system prompt for the enabled modes.

        Mirrors the if/elif chain previously duplicated between ``cli/chat.py``
        and ``WebServerConfig``:

        - a custom ``system_prompt`` wins;
        - ``no_system_prompt`` yields ``None``;
        - otherwise the default skills-advertising prompt applies.

        Returns:
            The effective system prompt, or ``None`` when none is used.
        """
        if self.system_prompt:
            return self.system_prompt
        if self.no_system_prompt:
            return None
        from janito.system_prompt import sync_default_sections

        return sync_default_sections().render()

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
            ``[]`` when tools must be suppressed (``-Z``), otherwise ``None``
            (the caller uses all available tools).
        """
        return [] if self.no_tools else None

    def enable_toolsets(self, *, extra: list[str] | None = None) -> None:
        """Enable additional toolsets (e.g. the web-only ``janitoweb``).

        Args:
            extra: Additional toolset names to enable unconditionally (e.g.
                the web-only ``"janitoweb"`` toolset).
        """
        from janito.tooling.tools_registry import add_toolset

        for name in extra or []:
            add_toolset(name)
