"""
Shared utilities to set up an agent together with a GenericPromptHandler that
both single–shot and chat modes can reuse.  Having one central place avoids the
code duplication that previously existed in `chat_mode.session.ChatSession` and
`single_shot_mode.handler.PromptHandler`.
"""

from __future__ import annotations

from janito.agent.setup_agent import create_configured_agent
from janito.cli.prompt_core import (
    PromptHandler as GenericPromptHandler,
)
from typing import Any, Optional


def setup_agent_and_prompt_handler(
    *,
    args: Any,
    provider_instance: Any,
    llm_driver_config: Any,
    role: Optional[str] = None,
    verbose_tools: bool = False,
    verbose_agent: bool = False,
    allowed_permissions: Optional[list[str]] = None,
    profile: Optional[str] = None,
    profile_system_prompt: Optional[str] = None,
    conversation_history: Any = None,
):
    """Create a configured *agent* as well as a *GenericPromptHandler* bound to
    that agent and return them as a tuple.

    This helper consolidates the repetitive boiler-plate that was scattered
    across *single-shot* and *chat* modes – both of which need an agent plus a
    prompt handler that points to that agent.
    """
    no_tools_mode = False
    if hasattr(args, "no_tools_mode"):
        no_tools_mode = getattr(args, "no_tools_mode", False)

    zero_mode = getattr(args, "zero", False)
    agent = create_configured_agent(
        provider_instance=provider_instance,
        llm_driver_config=llm_driver_config,
        role=role,
        verbose_tools=verbose_tools,
        verbose_agent=verbose_agent,
        allowed_permissions=allowed_permissions,
        profile=profile,
        profile_system_prompt=profile_system_prompt,
        zero_mode=zero_mode,
        no_tools_mode=no_tools_mode,
    )

    prompt_handler = GenericPromptHandler(
        args=args,
        conversation_history=conversation_history,
        provider_instance=provider_instance,
    )
    prompt_handler.agent = agent

    return agent, prompt_handler
