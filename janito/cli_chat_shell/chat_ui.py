from .ui import print_welcome, get_toolbar_func, get_prompt_session
from janito import __version__
from janito.agent.config import effective_config
from janito.agent.runtime_config import runtime_config


def setup_prompt_session(
    messages, last_usage_info_ref, last_elapsed, mem_history, profile_manager, agent
):
    model_name = getattr(agent, "model", None)

    def get_messages():
        return messages

    def get_usage():
        return last_usage_info_ref["value"]

    def get_elapsed():
        return last_elapsed

    session = get_prompt_session(
        get_toolbar_func(
            get_messages,
            get_usage,
            get_elapsed,
            model_name=model_name,
            role_ref=lambda: (
                "*using custom system prompt*"
                if (
                    runtime_config.get("system_prompt_template")
                    or runtime_config.get("system_prompt_template_file")
                )
                else (runtime_config.get("role") or effective_config.get("role"))
            ),
        ),
        mem_history,
    )
    return session


def print_welcome_message(console, continued):
    print_welcome(console, version=__version__, continued=continued)
