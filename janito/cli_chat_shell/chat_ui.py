from .ui import print_welcome, get_toolbar_func, get_prompt_session
from janito import __version__
from janito.agent.config import effective_config
from janito.agent.runtime_config import runtime_config
from .session_manager import get_session_id


def setup_prompt_session(
    messages,
    last_usage_info_ref,
    last_elapsed,
    mem_history,
    profile_manager,
    agent,
    history_ref,
):
    model_name = getattr(agent, "model", None)
    session_id = get_session_id()

    def get_messages():
        return messages

    def get_usage():
        return last_usage_info_ref()

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
            session_id=session_id,
            history_ref=history_ref,
        ),
        mem_history,
    )
    return session


def print_welcome_message(console, continued):
    print_welcome(console, version=__version__, continued=continued)
