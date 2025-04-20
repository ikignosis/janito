import jinja2
from pathlib import Path
from typing import List
import platform
import os


def parse_style_string(style: str) -> (str, List[str]):
    """Parse a style string like 'technical-allcommit' into main style and features."""
    if "-" in style:
        parts = style.split("-")
        return parts[0], parts[1:]
    return style, []


def get_platform_name() -> str:
    """Return a normalized platform name (windows, linux, darwin)."""
    sys_platform = platform.system().lower()
    if sys_platform.startswith("win"):
        return "windows"
    elif sys_platform.startswith("linux"):
        return "linux"
    elif sys_platform.startswith("darwin"):
        return "darwin"
    return sys_platform


def get_python_version() -> str:
    """Return the Python version as a string."""
    return platform.python_version()


def get_shell_info() -> str:
    """Detect the shell or environment in use (cmd, PowerShell, bash, git bash, wsl, etc.)."""
    shell = os.environ.get("SHELL")
    if shell:
        return shell
    # On Windows, check for common shells
    comspec = os.environ.get("COMSPEC")
    if comspec:
        if "powershell" in comspec.lower():
            return "PowerShell"
        elif "cmd" in comspec.lower():
            return "cmd.exe"
    # Git Bash/WSL detection
    if os.environ.get("MSYSTEM"):
        return f"Git Bash ({os.environ.get('MSYSTEM')})"
    if os.environ.get("WSL_DISTRO_NAME"):
        return f"WSL ({os.environ.get('WSL_DISTRO_NAME')})"
    return "unknown"


def render_system_prompt_template(
    role: str,
    interaction_style: str = "default",
    interaction_mode: str = "prompt",
    platform_name: str = None,
    python_version: str = None,
    shell_info: str = None,
) -> str:
    """
    Renders the system prompt template, supporting combinatorial styles.
    interaction_style: e.g., 'technical', 'default', or 'technical-allcommit'.
    platform_name: normalized platform string (windows, linux, darwin, etc.)
    python_version: Python version string
    shell_info: Detected shell/environment string
    """
    main_style, features = parse_style_string(interaction_style)
    base_dir = Path(__file__).parent / "agent" / "templates"
    profiles_dir = base_dir / "profiles"
    features_dir = base_dir / "features"
    loader = jinja2.ChoiceLoader(
        [
            jinja2.FileSystemLoader(str(profiles_dir)),
            jinja2.FileSystemLoader(str(features_dir)),
        ]
    )
    env = jinja2.Environment(loader=loader)

    # Determine main template filename
    if main_style == "technical":
        main_template = "system_prompt_template_technical.j2"
    else:
        main_template = "system_prompt_template.j2"

    # Platform/environment detection
    if platform_name is None:
        platform_name = get_platform_name()
    if python_version is None:
        python_version = get_python_version()
    if shell_info is None:
        shell_info = get_shell_info()

    # If no features, render as before
    if not features:
        template = env.get_template(main_template)
        return template.render(
            role=role,
            interaction_mode=interaction_mode,
            platform=platform_name,
            python_version=python_version,
            shell_info=shell_info,
        )

    # For features, chain inheritance: each feature template extends the previous
    parent_template = main_template
    context = {
        "role": role,
        "interaction_mode": interaction_mode,
        "platform": platform_name,
        "python_version": python_version,
        "shell_info": shell_info,
    }
    for feature in features:
        feature_template = f"system_prompt_template_{feature}.j2"
        template = env.get_template(feature_template)
        context["parent_template"] = parent_template
        rendered = template.render(**context)
        parent_template = feature_template
    return rendered


if __name__ == "__main__":
    # Example: technical-allcommit
    prompt = render_system_prompt_template(
        "software engineer",
        interaction_style="technical-allcommit",
        interaction_mode="prompt",
    )
    print(prompt)

# Combinatorial style system:
# - interaction_style can be e.g. 'technical-allcommit'
# - The first part is the main style, subsequent parts are feature extensions.
# - Each feature template (system_prompt_template_<feature>.j2) must use `{% extends parent_template %}` for dynamic inheritance.
# - Main styles are in templates/profiles/, features in templates/features/.
# - The 'platform', 'python_version', and 'shell_info' variables are always passed to templates.
# - See README_structure.txt for documentation.
