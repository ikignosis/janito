from openai import OpenAI
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from janito.agent.platform_discovery import get_platform_name, get_python_version
from janito.agent.platform_discovery import detect_shell


class AgentProfileManager:
    REFERER = "www.janito.dev"
    TITLE = "Janito"

    def set_role(self, new_role):
        """Set the agent's role and force prompt re-rendering."""
        self.role = new_role
        self.refresh_prompt()

    def render_prompt(self):
        base_dir = Path(__file__).parent / "templates"
        profiles_dir = base_dir / "profiles"
        if getattr(self, "lang", "en") == "pt":
            main_template_name = "system_prompt_template_base_pt.txt.j2"
        else:
            main_template_name = "system_prompt_template_base.txt.j2"
        platform_name = get_platform_name()
        python_version = get_python_version()
        shell_info = detect_shell()

        context = {
            "role": self.role,
            "interaction_mode": self.interaction_mode,
            "platform": platform_name,
            "python_version": python_version,
            "shell_info": shell_info,
        }
        env = Environment(
            loader=FileSystemLoader(str(profiles_dir)),
            autoescape=select_autoescape(["txt", "j2"]),
        )
        template = env.get_template(main_template_name)
        prompt = template.render(**context)
        return prompt

    def __init__(
        self,
        api_key,
        model,
        role,
        profile_name,
        interaction_mode,
        verbose_tools,
        base_url,
        azure_openai_api_version,
        use_azure_openai,
        lang="en",
    ):
        self.api_key = api_key
        self.model = model
        self.role = role
        self.profile_name = "base"
        self.interaction_mode = interaction_mode
        self.verbose_tools = verbose_tools
        self.base_url = base_url
        self.azure_openai_api_version = azure_openai_api_version
        self.use_azure_openai = use_azure_openai
        self.lang = lang
        if use_azure_openai:
            from openai import AzureOpenAI

            self.client = AzureOpenAI(
                api_key=api_key,
                azure_endpoint=base_url,
                api_version=azure_openai_api_version,
            )
        else:
            self.client = OpenAI(
                base_url=base_url,
                api_key=api_key,
                default_headers={"HTTP-Referer": self.REFERER, "X-Title": self.TITLE},
            )
        from janito.agent.openai_client import Agent

        self.agent = Agent(
            api_key=api_key,
            model=model,
            base_url=base_url,
            use_azure_openai=use_azure_openai,
            azure_openai_api_version=azure_openai_api_version,
        )
        self.system_prompt_template = None

    def refresh_prompt(self):
        self.system_prompt_template = self.render_prompt()
        self.agent.system_prompt_template = self.system_prompt_template


# All prompt rendering is now handled by AgentProfileManager.
