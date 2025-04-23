from openai import OpenAI
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from janito.agent.platform_discovery import get_platform_name, get_python_version
from janito.agent.platform_discovery import detect_shell
import sys
import itertools


class AgentProfileManager:
    def _report_template_not_found(self, template_name, search_dirs):
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

    def parse_profile_string(self, profile: str):
        # Expect profile in format communication-operational (e.g., concise-technical)
        if "-" in profile:
            parts = profile.split("-")
            if len(parts) == 2:
                return parts[0], parts[1]
        # fallback: treat as default
        return "concise", "technical"

    def render_prompt(self):
        comm_style, op_style = self.parse_profile_string(self.profile)
        base_dir = Path(__file__).parent / "templates"
        profiles_dir = base_dir / "profiles"
        # Always use the dynamic base template
        main_template_name = "system_prompt_template_base.txt.j2"
        # Compose fragment filenames
        comm_fragment = f"communication_style_{comm_style}.txt.j2"
        op_fragment = f"operational_style_{op_style}.txt.j2"
        comm_path = profiles_dir / comm_fragment
        op_path = profiles_dir / op_fragment
        # Validate existence
        if not comm_path.exists() or not op_path.exists():
            print(
                f"\n[janito] ⚠️ Profile fragment(s) not found: {comm_fragment if not comm_path.exists() else ''} {op_fragment if not op_path.exists() else ''}\n[janito] Defaulting to: concise-technical\n",
                file=sys.stderr,
            )
            comm_fragment = "communication_style_concise.txt.j2"
            op_fragment = "operational_style_technical.txt.j2"
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
            "operational_style_fragment": op_fragment,
            "communication_style_fragment": comm_fragment,
        }
        # Set up Jinja2 environment
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
        profile,
        interaction_mode,
        verbose_tools,
        base_url,
        azure_openai_api_version,
        use_azure_openai,
    ):
        self.api_key = api_key
        self.model = model
        self.role = role
        self.profile = profile
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

    def get_profile_combo(self):
        """
        Returns the actual communication-operational style combination as a string (e.g., 'concise-technical').
        Never returns 'default'.
        """
        comm_style, op_style = self.parse_profile_string(self.profile)
        return f"{comm_style}-{op_style}"

    def get_profiles_list(self):
        """
        Returns a list of all valid profile names as communication-operational pairs.
        """
        base_dir = Path(__file__).parent / "templates"
        profiles_dir = base_dir / "profiles"
        comm_styles = [
            p.stem.replace("communication_style_", "").split(".", 1)[0]
            for p in profiles_dir.glob("communication_style_*.txt.j2")
        ]
        op_styles = [
            p.stem.replace("operational_style_", "").split(".", 1)[0]
            for p in profiles_dir.glob("operational_style_*.txt.j2")
        ]
        return [f"{c}-{o}" for c, o in itertools.product(comm_styles, op_styles)]


# All prompt rendering is now handled by AgentProfileManager.
