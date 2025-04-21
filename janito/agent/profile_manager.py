from janito.agent.conversation import ConversationHandler
from openai import OpenAI
import jinja2
from pathlib import Path
import platform
import os


class AgentProfileManager:
    REFERER = "www.janito.dev"
    TITLE = "Janito"

    def parse_style_string(self, style: str):
        if "-" in style:
            parts = style.split("-")
            return parts[0], parts[1:]
        return style, []

    def get_platform_name(self):
        sys_platform = platform.system().lower()
        if sys_platform.startswith("win"):
            return "windows"
        elif sys_platform.startswith("linux"):
            return "linux"
        elif sys_platform.startswith("darwin"):
            return "darwin"
        return sys_platform

    def get_python_version(self):
        return platform.python_version()

    def get_shell_info(self):
        shell = os.environ.get("SHELL")
        if shell:
            return shell
        comspec = os.environ.get("COMSPEC")
        if comspec:
            if "powershell" in comspec.lower():
                return "PowerShell"
            elif "cmd" in comspec.lower():
                return "cmd.exe"
        if os.environ.get("MSYSTEM"):
            return f"Git Bash ({os.environ.get('MSYSTEM')})"
        if os.environ.get("WSL_DISTRO_NAME"):
            return f"WSL ({os.environ.get('WSL_DISTRO_NAME')})"
        return "unknown"

    def render_prompt(self):
        main_style, features = self.parse_style_string(self.interaction_style)
        base_dir = Path(__file__).parent / "templates"
        profiles_dir = base_dir / "profiles"
        features_dir = base_dir / "features"
        loader = jinja2.ChoiceLoader(
            [
                jinja2.FileSystemLoader(str(profiles_dir)),
                jinja2.FileSystemLoader(str(features_dir)),
            ]
        )
        env = jinja2.Environment(loader=loader)
        if main_style == "technical":
            main_template = "system_prompt_template_technical.j2"
        else:
            main_template = "system_prompt_template.j2"
        platform_name = self.get_platform_name()
        python_version = self.get_python_version()
        shell_info = self.get_shell_info()
        if not features:
            # Inject tech.txt existence and content
            tech_txt_path = Path(".janito") / "tech.txt"
            tech_txt_exists = tech_txt_path.exists()
            tech_txt_content = ""
            if tech_txt_exists:
                try:
                    tech_txt_content = tech_txt_path.read_text(encoding="utf-8")
                except Exception:
                    tech_txt_content = "⚠️ Error reading janito/tech.txt."
            template = env.get_template(main_template)
            return template.render(
                role=self.role,
                interaction_mode=self.interaction_mode,
                platform=platform_name,
                python_version=python_version,
                shell_info=shell_info,
                tech_txt_exists=tech_txt_exists,
                tech_txt_content=tech_txt_content,
            )
        parent_template = main_template
        # Inject tech.txt existence and content for feature templates as well
        tech_txt_path = Path(".janito") / "tech.txt"
        tech_txt_exists = tech_txt_path.exists()
        tech_txt_content = ""
        if tech_txt_exists:
            try:
                tech_txt_content = tech_txt_path.read_text(encoding="utf-8")
            except Exception:
                tech_txt_content = "⚠️ Error reading janito/tech.txt."
        context = {
            "role": self.role,
            "interaction_mode": self.interaction_mode,
            "platform": platform_name,
            "python_version": python_version,
            "shell_info": shell_info,
            "tech_txt_exists": tech_txt_exists,
            "tech_txt_content": tech_txt_content,
        }
        for feature in features:
            feature_template = f"system_prompt_template_{feature}.j2"
            template = env.get_template(feature_template)
            context["parent_template"] = parent_template
            rendered = template.render(**context)
            parent_template = feature_template
        return rendered

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
        self.agent = ConversationHandler(self.client, model)
        self.system_prompt_template = None

    def refresh_prompt(self):
        self.system_prompt_template = self.render_prompt()
        self.agent.system_prompt_template = self.system_prompt_template


# All prompt rendering is now handled by AgentProfileManager.
