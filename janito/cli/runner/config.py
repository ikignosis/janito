from janito.agent.profile_manager import AgentProfileManager
from janito.agent.runtime_config import unified_config, runtime_config
from janito.agent.config import get_api_key


def get_system_prompt_template(args, role):
    system_prompt_template = None
    if getattr(args, "system_prompt_template_file", None):
        with open(args.system_prompt_template_file, "r", encoding="utf-8") as f:
            system_prompt_template = f.read()
        runtime_config.set(
            "system_prompt_template_file", args.system_prompt_template_file
        )
    else:
        system_prompt_template = getattr(
            args, "system_prompt_template", None
        ) or unified_config.get("system_prompt_template")
        if getattr(args, "system_prompt_template", None):
            runtime_config.set("system_prompt_template", system_prompt_template)
        if system_prompt_template is None:
            profile_manager = AgentProfileManager(
                api_key=get_api_key(),
                model=unified_config.get("model"),
                role=role,
                profile_name="base",
                interaction_mode=unified_config.get("interaction_mode", "prompt"),
                verbose_tools=unified_config.get("verbose_tools", False),
                base_url=unified_config.get("base_url", None),
                azure_openai_api_version=unified_config.get(
                    "azure_openai_api_version", "2023-05-15"
                ),
                use_azure_openai=unified_config.get("use_azure_openai", False),
            )
            system_prompt_template = profile_manager.system_prompt_template
    return system_prompt_template
