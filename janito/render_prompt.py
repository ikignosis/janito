import jinja2
from pathlib import Path
from typing import List
import platform


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


def render_system_prompt_template(
    role: str,
    interaction_style: str = "default",
    interaction_mode: str = "prompt",
    platform_name: str = None,
) -> str:
    """
    Renders the system prompt template, supporting combinatorial styles.
    interaction_style: e.g., 'technical', 'default', or 'technical-allcommit'.
    platform_name: normalized platform string (windows, linux, darwin, etc.)
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

    # Platform detection
    if platform_name is None:
        platform_name = get_platform_name()

    # If no features, render as before
    if not features:
        template = env.get_template(main_template)
        return template.render(
            role=role, interaction_mode=interaction_mode, platform=platform_name
        )

    # For features, chain inheritance: each feature template extends the previous
    parent_template = main_template
    context = {
        "role": role,
        "interaction_mode": interaction_mode,
        "platform": platform_name,
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
# - The 'platform' variable is always passed to templates (windows, linux, darwin, etc.).
# - See README_structure.txt for documentation.
