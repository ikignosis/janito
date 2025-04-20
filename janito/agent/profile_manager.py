from janito.agent.agent import Agent
from janito.render_prompt import render_system_prompt


class AgentProfileManager:
    def __init__(
        self,
        api_key,
        model=None,
        role="software engineer",
        interaction_style="default",
        **agent_kwargs,
    ):
        self.role = role
        self.interaction_style = interaction_style
        self.system_prompt = self.render_prompt()
        self.agent = Agent(
            api_key=api_key,
            model=model,
            system_prompt=self.system_prompt,
            **agent_kwargs,
        )

    def render_prompt(self):
        return render_system_prompt(self.role, interaction_style=self.interaction_style)

    def set_role(self, new_role):
        self.role = new_role
        self.refresh_prompt()

    def set_interaction_style(self, new_style):
        self.interaction_style = new_style
        self.refresh_prompt()

    def refresh_prompt(self):
        self.system_prompt = self.render_prompt()
        self.agent.system_prompt = self.system_prompt

    def chat(self, *args, **kwargs):
        return self.agent.chat(*args, **kwargs)
