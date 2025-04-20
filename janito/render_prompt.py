import jinja2
from pathlib import Path


def render_system_prompt(role: str, interaction_style: str = "default") -> str:
    template_name = "system_instructions.j2"
    if interaction_style == "technical":
        template_name = "system_instructions_technical.j2"
    template_loader = jinja2.FileSystemLoader(
        searchpath=str(Path(__file__).parent / "agent" / "templates")
    )
    env = jinja2.Environment(loader=template_loader)
    template = env.get_template(template_name)
    return template.render(role=role)


if __name__ == "__main__":
    prompt = render_system_prompt("software engineer", interaction_style="technical")
    print(prompt)
