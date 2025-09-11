from janito.llm.model import LLMModelInfo

MODEL_SPECS = {
    "qwen-turbo": LLMModelInfo(
        name="qwen-turbo",
        context=1008192,
        max_response=8192,
        category="Alibaba Qwen Turbo Model (OpenAI-compatible)",
        driver="OpenAIModelDriver",
        thinking_supported=True,
        thinking=False,
        max_cot=8192,
    ),
    "qwen-plus": LLMModelInfo(
        name="qwen-plus",
        context=131072,
        max_response=8192,
        category="Alibaba Qwen Plus Model (OpenAI-compatible)",
        driver="OpenAIModelDriver",
        thinking_supported=True,
        thinking=False,
        max_cot=8192,
    ),
    "qwen-flash": LLMModelInfo(
        name="qwen-flash",
        context=1000000,
        max_response=8192,
        category="Alibaba Qwen Flash Model (OpenAI-compatible)",
        driver="OpenAIModelDriver",
        thinking_supported=True,
        thinking=False,
        max_cot=8192,
    ),
    "qwen-max": LLMModelInfo(
        name="qwen-max",
        context=32768,
        max_response=8192,
        category="Alibaba Qwen Max Model (OpenAI-compatible)",
        driver="OpenAIModelDriver",
        thinking_supported=True,
        thinking=False,
        max_cot=8192,
    ),
    "qwen3-coder-plus": LLMModelInfo(
        name="qwen3-coder-plus",
        context=1048576,
        max_response=65536,
        category="Alibaba Qwen3 Coder Plus Model (OpenAI-compatible)",
        driver="OpenAIModelDriver",
        thinking_supported=True,
        thinking=False,
        max_cot=65536,
    ),
    "qwen3-coder-480b-a35b-instruct": LLMModelInfo(
        name="qwen3-coder-480b-a35b-instruct",
        context=262144,
        max_response=65536,
        category="Alibaba Qwen3 Coder 480B A35B Instruct Model (OpenAI-compatible)",
        driver="OpenAIModelDriver",
        thinking_supported=True,
        thinking=False,
        max_cot=65536,
    ),
    # Qwen3 1M context models (July 2025 update)
    "qwen3-235b-a22b-thinking-2507": LLMModelInfo(
        name="qwen3-235b-a22b-thinking-2507",
        context=131072,  # Supports up to 1M with special config
        max_response=32768,
        category="Alibaba Qwen3 235B A22B Thinking Model (OpenAI-compatible)",
        driver="OpenAIModelDriver",
        thinking=True,
        thinking_supported=True,
        max_cot=32768,
    ),
    "qwen3-235b-a22b-instruct-2507": LLMModelInfo(
        name="qwen3-235b-a22b-instruct-2507",
        context=129024,  # Supports up to 1M with special config
        max_response=32768,
        category="Alibaba Qwen3 235B A22B Instruct Model (OpenAI-compatible)",
        driver="OpenAIModelDriver",
        thinking_supported=True,
        thinking=False,
        max_cot=32768,
    ),
    "qwen3-30b-a3b-thinking-2507": LLMModelInfo(
        name="qwen3-30b-a3b-thinking-2507",
        context=126976,  # Supports up to 1M with special config
        max_response=32768,
        category="Alibaba Qwen3 30B A3B Thinking Model (OpenAI-compatible)",
        driver="OpenAIModelDriver",
        thinking=True,
        thinking_supported=True,
        max_cot=32768,
    ),
    "qwen3-30b-a3b-instruct-2507": LLMModelInfo(
        name="qwen3-30b-a3b-instruct-2507",
        context=129024,  # Supports up to 1M with special config
        max_response=32768,
        category="Alibaba Qwen3 30B A3B Instruct Model (OpenAI-compatible)",
        driver="OpenAIModelDriver",
        thinking_supported=True,
        thinking=False,
        max_cot=32768,
    ),
    # Qwen3 Next models (September 2025 update)
    "qwen3-next-80b-a3b-instruct": LLMModelInfo(
        name="qwen3-next-80b-a3b-instruct",
        context=262144,  # 256K context window (Qwen3-Max Preview)
        max_response=65536,  # Matches Qwen3-Max Preview output limit
        category="Alibaba Qwen3-Max Preview (256K) - 80B A3B Instruct Model (OpenAI-compatible)",
        driver="OpenAIModelDriver",
        thinking_supported=True,
        thinking=False,
        max_cot=65536,
    ),
    "qwen3-next-80b-a3b-thinking": LLMModelInfo(
        name="qwen3-next-80b-a3b-thinking",
        context=262144,  # 256K context window (Qwen3-Max Preview)
        max_response=65536,  # Matches Qwen3-Max Preview output limit
        category="Alibaba Qwen3-Max Preview (256K) - 80B A3B Thinking Model (OpenAI-compatible)",
        driver="OpenAIModelDriver",
        thinking=True,
        thinking_supported=True,
        max_cot=65536,
    ),
    "qwen3-max-preview": LLMModelInfo(
        name="qwen3-max-preview",
        context=262144,  # 256K context window (Qwen3-Max Preview)
        max_response=65536,  # Matches Qwen3-Max Preview output limit
        category="Alibaba Qwen3-Max Preview (256K) - Standard Model (OpenAI-compatible)",
        driver="OpenAIModelDriver",
        thinking_supported=True,
        thinking=False,
        max_cot=65536,
    ),
}
