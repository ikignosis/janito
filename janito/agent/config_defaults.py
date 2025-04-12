# Centralized config defaults for Janito
CONFIG_DEFAULTS = {
    "api_key": None,  # Must be set by user
    "model": "openrouter/optimus-alpha",    # Default model
    "base_url": "https://openrouter.ai/api/v1",
    "role": "software engineer",
    "system_prompt": None,  # None means auto-generate from role
    "temperature": 0.2,
    "max_tokens": 200000,
}
