import re
from pathlib import Path

from janito.llm.agent import LLMAgent
from janito.tooling import get_local_tools_adapter

from janito.agent.system_prompt import SystemPromptTemplateManager


def _create_agent(
    provider_instance,
    tools_provider,
    role,
    system_prompt,
    input_queue,
    output_queue,
    verbose_agent,
    context,
    template_path,
    profile,
):
    """
    Creates and returns an LLMAgent instance with the provided parameters.
    """
    agent = LLMAgent(
        provider_instance,
        tools_provider,
        agent_name=role or "developer",
        system_prompt=system_prompt,
        input_queue=input_queue,
        output_queue=output_queue,
        verbose_agent=verbose_agent,
    )
    agent.template_vars["role"] = context["role"]
    agent.template_vars["profile"] = profile
    agent.system_prompt_template = str(template_path)
    agent._template_vars = context.copy()
    agent._original_template_vars = context.copy()
    return agent


def setup_agent(
    provider_instance,
    llm_driver_config,
    role=None,
    templates_dir=None,
    zero_mode=False,
    input_queue=None,
    output_queue=None,
    verbose_tools=False,
    verbose_agent=False,
    allowed_permissions=None,
    profile=None,
    profile_system_prompt=None,
    no_tools_mode=False,
):
    """
    Creates an agent. A system prompt is rendered from a template only when a profile is specified.
    """
    if no_tools_mode or zero_mode:
        tools_provider = None
    else:
        tools_provider = get_local_tools_adapter()
        tools_provider.set_verbose_tools(verbose_tools)

    # If zero_mode is enabled or no profile is given we skip the system prompt.
    if zero_mode or (profile is None and profile_system_prompt is None):
        agent = LLMAgent(
            provider_instance,
            tools_provider,
            agent_name=role or "developer",
            system_prompt=None,
            input_queue=input_queue,
            output_queue=output_queue,
            verbose_agent=verbose_agent,
        )
        if role:
            agent.template_vars["role"] = role
        return agent

    # If profile_system_prompt is set, use it directly
    if profile_system_prompt is not None:
        agent = LLMAgent(
            provider_instance,
            tools_provider,
            agent_name=role or "developer",
            system_prompt=profile_system_prompt,
            input_queue=input_queue,
            output_queue=output_queue,
            verbose_agent=verbose_agent,
        )
        agent.template_vars["role"] = role or "developer"
        agent.template_vars["profile"] = None
        agent.template_vars["profile_system_prompt"] = profile_system_prompt
        return agent

    # Normal flow (profile-specific system prompt)
    if templates_dir is None:
        templates_dir = Path(__file__).parent / "templates" / "profiles"

    spm = SystemPromptTemplateManager(templates_dir=templates_dir)
    rendered_prompt, context, template_path = spm.render_profile(
        profile=profile,
        role=role,
        allowed_permissions=allowed_permissions,
    )

    return _create_agent(
        provider_instance,
        tools_provider,
        role,
        rendered_prompt,
        input_queue,
        output_queue,
        verbose_agent,
        context,
        template_path,
        profile,
    )


def create_configured_agent(
    *,
    provider_instance=None,
    llm_driver_config=None,
    role=None,
    verbose_tools=False,
    verbose_agent=False,
    templates_dir=None,
    zero_mode=False,
    allowed_permissions=None,
    profile=None,
    profile_system_prompt=None,
    no_tools_mode=False,
):
    """
    Normalizes agent setup for all CLI modes.

    Args:
        provider_instance: Provider instance for the agent
        llm_driver_config: LLM driver configuration
        role: Optional role string
        verbose_tools: Optional, default False
        verbose_agent: Optional, default False
        templates_dir: Optional
        zero_mode: Optional, default False

    Returns:
        Configured agent instance
    """
    input_queue = None
    output_queue = None
    driver = None
    if hasattr(provider_instance, "create_driver"):
        driver = provider_instance.create_driver()
        # Ensure no tools are passed to the driver when --no-tools flag is active
        if no_tools_mode:
            driver.tools_adapter = None
        driver.start()  # Ensure the driver background thread is started
        input_queue = getattr(driver, "input_queue", None)
        output_queue = getattr(driver, "output_queue", None)

    agent = setup_agent(
        provider_instance=provider_instance,
        llm_driver_config=llm_driver_config,
        role=role,
        templates_dir=templates_dir,
        zero_mode=zero_mode,
        input_queue=input_queue,
        output_queue=output_queue,
        verbose_tools=verbose_tools,
        verbose_agent=verbose_agent,
        allowed_permissions=allowed_permissions,
        profile=profile,
        profile_system_prompt=profile_system_prompt,
        no_tools_mode=no_tools_mode,
    )
    if driver is not None:
        agent.driver = driver  # Attach driver to agent for thread management
    return agent
