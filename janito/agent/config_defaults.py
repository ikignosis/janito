# Centralized config defaults for Janito
CONFIG_DEFAULTS = {
    "api_key": None,  # Must be set by user
    "model": "openai/gpt-4.1",  # Default model
    "base_url": "https://openrouter.ai/api/v1",
    "role": "software engineer",  # Part of the Agent Profile
    "system_prompt": None,  # None means auto-generate from Agent Profile role
    "temperature": 0.2,
    "max_tokens": 200000,
    "use_azure_openai": False,
    "interaction_style": "default",
}
