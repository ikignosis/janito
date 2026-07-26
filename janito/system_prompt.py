SYSTEM_PROMPT = """
- Explore the current directory for potential content related to the question
- In case of ambiguity or multiple options, ask for clarification before answering
"""


def get_system_prompt_with_skills() -> str:
    """Get the base system prompt with skills advertisement appended."""
    from .tooling.tools_registry import get_skills_section
    return SYSTEM_PROMPT + get_skills_section()
# - Before answering, explore the content related to the question
# - Use the namespace functions to deliver the code changes instead of showing the code.
