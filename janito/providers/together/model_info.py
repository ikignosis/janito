"""
Model specifications for Together AI provider.
"""

MODEL_SPECS = {
    "allenai/OLMo-2-0325-32B-Instruct": {
        "max_tokens": 32768,
        "max_input_tokens": 32768,
        "max_output_tokens": 32768,
        "description": "OLMo 2 32B Instruct - Fully open language model from AllenAI",
        "supports_tools": True,
        "supports_system_prompt": True,
        "supports_streaming": True,
    },
    "allenai/OLMo-2-1124-7B-Instruct": {
        "max_tokens": 32768,
        "max_input_tokens": 32768,
        "max_output_tokens": 32768,
        "description": "OLMo 2 7B Instruct - Fully open language model from AllenAI",
        "supports_tools": True,
        "supports_system_prompt": True,
        "supports_streaming": True,
    },
    "allenai/OLMo-2-0425-1B": {
        "max_tokens": 32768,
        "max_input_tokens": 32768,
        "max_output_tokens": 32768,
        "description": "OLMo 2 1B - Fully open language model from AllenAI",
        "supports_tools": True,
        "supports_system_prompt": True,
        "supports_streaming": True,
    },
    "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo": {
        "max_tokens": 8192,
        "max_input_tokens": 128000,
        "max_output_tokens": 8192,
        "description": "Llama 3.1 8B Instruct Turbo",
        "supports_tools": True,
        "supports_system_prompt": True,
        "supports_streaming": True,
    },
    "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo": {
        "max_tokens": 8192,
        "max_input_tokens": 128000,
        "max_output_tokens": 8192,
        "description": "Llama 3.1 70B Instruct Turbo",
        "supports_tools": True,
        "supports_system_prompt": True,
        "supports_streaming": True,
    },
    "mistralai/Mixtral-8x7B-Instruct-v0.1": {
        "max_tokens": 32768,
        "max_input_tokens": 32768,
        "max_output_tokens": 32768,
        "description": "Mixtral 8x7B Instruct",
        "supports_tools": True,
        "supports_system_prompt": True,
        "supports_streaming": True,
    },
    "deepseek-ai/deepseek-llm-67b-chat": {
        "max_tokens": 4096,
        "max_input_tokens": 4096,
        "max_output_tokens": 4096,
        "description": "DeepSeek LLM 67B Chat",
        "supports_tools": True,
        "supports_system_prompt": True,
        "supports_streaming": True,
    },
}