# Centralized config defaults for Janito
CONFIG_DEFAULTS = {
    "api_key": None,  # Must be set by user
    "model": "openai/gpt-4.1",  # Default model
    "base_url": "https://openrouter.ai/api/v1",
    "role": "software developer",  # Part of the Agent Profile
    "system_prompt_template": None,  # None means auto-generate from Agent Profile role
    "temperature": 0.2,
    "max_tokens": 200000,
    "use_azure_openai": False,
    "azure_openai_api_version": "2023-05-15",
    "profile": "base",
    "providers": {
        "openai": {
            "api_key": None,
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-3.5-turbo",
        },
        "azureai": {
            "api_key": None,
            "base_url": "https://your-azure-endpoint.openai.azure.com/",
            "api_version": "2023-05-15",
            "default_model": "gpt-35-turbo",
        },
        "openrouterai": {
            "api_key": None,
            "base_url": "https://openrouter.ai/api/v1",
            "default_model": "openrouter/cognitive",
        },
        "fireworksai": {
            "api_key": None,
            "base_url": "https://api.fireworks.ai/inference/v1",
            "default_model": "accounts/fireworks/models/firefunction-v1",
        },
    },
}
