from janito.agent.conversation import ConversationHandler


class AgentProfileManager:
    def __init__(
        self,
        api_key,
        model,
        role,
        interaction_style,
        interaction_mode,
        verbose_tools,
        base_url,
        azure_openai_api_version,
        use_azure_openai,
    ):
        self.api_key = api_key
        self.model = model
        self.role = role
        self.interaction_style = interaction_style
        self.interaction_mode = interaction_mode
        self.verbose_tools = verbose_tools
        self.base_url = base_url
        self.azure_openai_api_version = azure_openai_api_version
        self.use_azure_openai = use_azure_openai
        self.agent = ConversationHandler(self, model)
        self.system_prompt_template = None

    def refresh_prompt(self):
        self.system_prompt_template = self.render_prompt()
        self.agent.system_prompt_template = self.system_prompt_template

    def chat(self, *args, **kwargs):
        # Explicitly forward verbose_response, verbose_events, verbose_stream if present
        return self.agent.handle_conversation(*args, **kwargs)


# Supports combinatorial styles (e.g., 'technical-commit_all'), propagates interaction_mode and platform to the prompt renderer.
