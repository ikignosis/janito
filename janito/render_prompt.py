import jinja2
from pathlib import Path

from janito.agent.runtime_config import unified_config

def render_system_prompt(role: str) -> str:
    template_loader = jinja2.FileSystemLoader(searchpath=str(Path(__file__).parent / "templates"))
    env = jinja2.Environment(loader=template_loader)
    template = env.get_template("system_instructions.j2")
    return template.render(role=role)

if __name__ == "__main__":
    prompt = render_system_prompt("software engineer")
    print(prompt)
