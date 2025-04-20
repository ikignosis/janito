import os


def load_prompt(filename=None):
    """
    Load the system prompt from a file. If filename is None, use the default prompt file.
    Returns the prompt string.
    """
    if filename is None:
        # Default prompt file path (can be customized)
        filename = os.path.join(
            os.path.dirname(__file__), "../agent/templates/system_instructions.j2"
        )
    filename = os.path.abspath(filename)
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Prompt file not found: {filename}")
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()
