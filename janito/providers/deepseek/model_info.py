from janito.llm.model import LLMModelInfo

MODEL_SPECS = {
    "deepseek-chat": LLMModelInfo(
        name="deepseek-chat",
        context=8192,
        max_response=4096,
        driver="OpenAIModelDriver",
    ),
    "deepseek-reasoner": LLMModelInfo(
        name="deepseek-reasoner",
        context=8192,
        max_response=4096,
        driver="OpenAIModelDriver",
    ),
}
