"""Model specifications for Cerebras Inference API."""

from janito.llm.model import LLMModelInfo

MODEL_SPECS = {
    "qwen-3-32b": LLMModelInfo(
        name="qwen-3-32b",
        max_input=128000,
        max_response=16384,
        default_temp=0.7,
        driver="CerebrasModelDriver",
        other={
            "description": "Qwen 3 32B model for general instruction following",
            "pricing": {"input_per_1k_tokens": 0.0002, "output_per_1k_tokens": 0.0006},
        },
    ),
    "qwen-3-235b-a22b-instruct-2507": LLMModelInfo(
        name="qwen-3-235b-a22b-instruct-2507",
        max_input=128000,
        max_response=16384,
        default_temp=0.7,
        driver="CerebrasModelDriver",
        other={
            "description": "Qwen 3 235B A22B instruction-tuned model (preview)",
            "pricing": {"input_per_1k_tokens": 0.001, "output_per_1k_tokens": 0.003},
        },
    ),
    "qwen-3-235b-a22b-thinking-2507": LLMModelInfo(
        name="qwen-3-235b-a22b-thinking-2507",
        max_input=128000,
        max_response=16384,
        default_temp=0.7,
        driver="CerebrasModelDriver",
        other={
            "description": "Qwen 3 235B A22B thinking model for reasoning tasks (preview)",
            "pricing": {"input_per_1k_tokens": 0.001, "output_per_1k_tokens": 0.003},
        },
    ),
    "qwen-3-coder-480b": LLMModelInfo(
        name="qwen-3-coder-480b",
        max_input=128000,
        max_response=16384,
        default_temp=0.7,
        driver="CerebrasModelDriver",
        other={
            "description": "Qwen 3 Coder 480B model for programming tasks (preview)",
            "pricing": {"input_per_1k_tokens": 0.002, "output_per_1k_tokens": 0.006},
        },
    ),
    "gpt-oss-120b": LLMModelInfo(
        name="gpt-oss-120b",
        max_input=128000,
        max_response=16384,
        default_temp=0.7,
        driver="CerebrasModelDriver",
        other={
            "description": "GPT-OSS 120B open-source model (preview)",
            "pricing": {"input_per_1k_tokens": 0.0008, "output_per_1k_tokens": 0.0024},
        },
    ),
}
