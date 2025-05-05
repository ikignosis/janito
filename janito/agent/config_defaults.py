# Centralized config defaults for Janito
CONFIG_DEFAULTS = {
    "api_key": None,  # Must be set by user
    "model": "gpt-4.1",  # Default model
    "role": "software developer",  # Part of the Agent Profile
    "system_prompt_template": None,  # None means auto-generate from Agent Profile role
    "temperature": 0.2,
    "max_tokens": 32000,
    "use_azure_openai": False,
    "azure_openai_api_version": "2023-05-15",
    "profile": "base",
}
