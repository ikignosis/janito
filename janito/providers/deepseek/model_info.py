MODEL_SPECS = {
    "deepseek-chat": {
        "description": "DeepSeek Chat Model (OpenAI-compatible)",
        "context_window": 8192,
        "max_tokens": 4096,
        "family": "deepseek",
        "default": True,
    },
    "deepseek-reasoner": {
        "description": "DeepSeek Reasoner Model (OpenAI-compatible)",
        "context_window": 8192,
        "max_tokens": 4096,
        "family": "deepseek",
        "default": False,
    },
    "deepseek-v3.1": {
        "description": "DeepSeek V3.1 Model (128K context, OpenAI-compatible)",
        "context_window": 131072,
        "max_tokens": 4096,
        "family": "deepseek",
        "default": False,
    },
    "deepseek-v3.1-base": {
        "description": "DeepSeek V3.1 Base Model (128K context, OpenAI-compatible)",
        "context_window": 131072,
        "max_tokens": 4096,
        "family": "deepseek",
        "default": False,
    },
    "deepseek-r1": {
        "description": "DeepSeek R1 Model (128K context, OpenAI-compatible)",
        "context_window": 131072,
        "max_tokens": 4096,
        "family": "deepseek",
        "default": False,
    },
}
