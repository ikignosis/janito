import os
import importlib.resources


def load_prompt(filename=None):
    """
    Load the system prompt from a file. If filename is None, use the default prompt file.
    Returns the prompt string.
    Tries source path first, then falls back to importlib.resources for installed packages.
    """
    default_rel_path = os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "../agent/templates/profiles/system_prompt_template_default.j2",
        )
    )
    if filename is None:
        filename = default_rel_path

    # Try loading from source path first
    abs_path = os.path.abspath(filename)
    if os.path.exists(abs_path):
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read()

    # If not found, try importlib.resources (for installed package)
    try:
        # Remove leading directories up to 'janito/agent/templates'
        # and get the relative path inside the package
        resource_path = filename
        for marker in ["janito/agent/templates/", "agent/templates/"]:
            idx = filename.replace("\\", "/").find(marker)
            if idx != -1:
                resource_path = filename[idx + len("janito/agent/templates/") :]
                break

        # Try loading from janito.agent.templates.profiles
        if resource_path.startswith("profiles/"):
            package = "janito.agent.templates.profiles"
            resource = resource_path[len("profiles/") :]
        elif resource_path.startswith("features/"):
            package = "janito.agent.templates.features"
            resource = resource_path[len("features/") :]
        else:
            package = "janito.agent.templates"
            resource = resource_path

        with (
            importlib.resources.files(package)
            .joinpath(resource)
            .open("r", encoding="utf-8") as f
        ):
            return f.read()
    except Exception as e:
        raise FileNotFoundError(
            f"Prompt file not found at '{abs_path}' or in package resources: {e}"
        )
