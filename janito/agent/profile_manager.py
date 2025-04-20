from janito.agent.openai_client import Agent
from janito.render_prompt import render_system_prompt_template, get_platform_name


class AgentProfileManager:
    def __init__(
        self,
        api_key,
        model=None,
        role="software engineer",
        interaction_style="default",
        interaction_mode="prompt",
        **agent_kwargs,
    ):
        self.role = role
        self.interaction_style = interaction_style
        self.interaction_mode = interaction_mode
        self.platform = get_platform_name()
        self.system_prompt_template = self.render_prompt()
        self.agent = Agent(
            api_key=api_key,
            model=model,
            system_prompt_template=self.system_prompt_template,
            **agent_kwargs,
        )

    def render_prompt(self):
        return render_system_prompt_template(
            self.role,
            interaction_style=self.interaction_style,
            interaction_mode=self.interaction_mode,
            platform_name=self.platform,
        )

    def set_role(self, new_role):
        self.role = new_role
        self.refresh_prompt()

    def set_interaction_style(self, new_style):
        self.interaction_style = new_style
        self.refresh_prompt()

    def set_interaction_mode(self, new_mode):
        self.interaction_mode = new_mode
        self.refresh_prompt()

    def set_platform(self, new_platform):
        self.platform = new_platform
        self.refresh_prompt()

    def refresh_prompt(self):
        self.system_prompt_template = self.render_prompt()
        self.agent.system_prompt_template = self.system_prompt_template

    def chat(self, *args, **kwargs):
        # Explicitly forward verbose_response and verbose_events if present
        return self.agent.chat(*args, **kwargs)


# Supports combinatorial styles (e.g., 'technical-allcommit'), propagates interaction_mode and platform to the prompt renderer.
