from janito.llm.model import LLMModelInfo

DEFAULT_MODEL = "deepseek-chat"

MODEL_SPECS = {
    "deepseek-chat": LLMModelInfo(
        name="deepseek-chat",
        context=131072,  # 128K context
        max_response=4096,  # Default 4K, Maximum 8K
        driver="OpenAIModelDriver",
    ),
    "deepseek-reasoner": LLMModelInfo(
        name="deepseek-reasoner",
        context=131072,  # 128K context
        max_response=32768,  # Default 32K, Maximum 64K
        driver="OpenAIModelDriver",
    ),
}
