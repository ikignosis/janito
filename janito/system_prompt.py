import os

SYSTEM_PROMPT = """
- Explore the current directory for potential content related to the question
"""


def get_system_prompt_with_skills() -> str:
    """Get the base system prompt with skills advertisement appended."""
    from .tooling.tools_registry import get_skills_section

    prompt = SYSTEM_PROMPT + get_skills_section()

    agents_md_path = os.path.join(os.getcwd(), "AGENTS.md")
    if os.path.isfile(agents_md_path):
        try:
            with open(agents_md_path, encoding="utf-8") as f:
                agents_content = f.read().strip()
            if agents_content:
                prompt += (
                    "\n\n## Project-Specific Instructions (from AGENTS.md)\n\n"
                    + agents_content
                    + "\n"
                )
        except OSError:
            pass  # If the file can't be read, just skip it

    return prompt


# - Before answering, explore the content related to the question
# - Use the namespace functions to deliver the code changes instead of showing the code.
