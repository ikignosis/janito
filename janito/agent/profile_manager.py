from openai import OpenAI
import toml
from string import Template
from pathlib import Path
from janito.agent.platform_discovery import get_platform_name, get_python_version
from janito.agent.platform_discovery import detect_shell


class AgentProfileManager:
    def _report_template_not_found(self, template_name, search_dirs):
        import sys

        search_dirs_str = ", ".join(str(d) for d in search_dirs)
        print(
            f"❗ TemplateNotFound: '{template_name}'\n  Searched paths: {search_dirs_str}",
            file=sys.stderr,
        )

    REFERER = "www.janito.dev"
    TITLE = "Janito"

    def set_role(self, new_role):
        """Set the agent's role and force prompt re-rendering."""
        self.role = new_role
        self.refresh_prompt()

    def parse_style_string(self, style: str):
        if "-" in style:
            parts = style.split("-")
            return parts[0], parts[1:]
        return style, []

    def render_prompt(self):
        main_style, features = self.parse_style_string(self.interaction_style)
        base_dir = Path(__file__).parent / "templates"
        profiles_dir = base_dir / "profiles"
        # Determine which TOML profile to use
        if main_style == "technical":
            main_template = profiles_dir / "system_prompt_template_technical.toml"
        else:
            main_template = profiles_dir / "system_prompt_template_default.toml"
        # Gather context variables
        platform_name = get_platform_name()
        python_version = get_python_version()
        shell_info = detect_shell()
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
            "tech_txt_exists": str(tech_txt_exists),
            "tech_txt_content": tech_txt_content,
        }

        # Load and merge TOML templates (handle inheritance)
        def load_toml_with_inheritance(path):
            data = toml.load(path)
            if "extends" in data:
                base_path = profiles_dir / data["extends"]
                base_data = toml.load(base_path)
                base_data.update({k: v for k, v in data.items() if k != "extends"})
                return base_data
            return data

        toml_data = load_toml_with_inheritance(main_template)
        # Merge in feature-specific TOML if any
        for feature in features:
            feature_template = profiles_dir / f"system_prompt_template_{feature}.toml"
            if feature_template.exists():
                feature_data = toml.load(feature_template)
                toml_data.update(
                    {k: v for k, v in feature_data.items() if k != "extends"}
                )

        # Render the TOML structure as a prompt string
        def render_section(section):
            if isinstance(section, dict):
                out = []
                for k, v in section.items():
                    if isinstance(v, list):
                        out.append(f"{k}:")
                        for item in v:
                            out.append(f"  - {item}")
                    else:
                        out.append(f"{k}: {v}")
                return "\n".join(out)
            elif isinstance(section, list):
                return "\n".join(f"- {item}" for item in section)
            else:
                return str(section)

        prompt_sections = []
        for section, value in toml_data.items():
            if section == "extends":
                continue
            prompt_sections.append(f"[{section}]")
            prompt_sections.append(render_section(value))
            prompt_sections.append("")
        prompt_template = "\n".join(prompt_sections)
        # Substitute variables
        prompt = Template(prompt_template).safe_substitute(context)
        return prompt

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
