from janito.llm.model import LLMModelInfo

MOONSHOT_MODEL_SPECS = {
    "kimi-k2-0711-preview": LLMModelInfo(
        name="kimi-k2-0711-preview",
        context=128000,
        max_input=100000,
        max_cot="N/A",
        max_response=4096,
        thinking_supported=False,
        default_temp=0.2,
        open="moonshot",
        driver="OpenAIModelDriver",
    ),
    "kimi-k2-turbo-preview": LLMModelInfo(
        name="kimi-k2-turbo-preview",
        context=128000,
        max_input=100000,
        max_cot="N/A",
        max_response=4096,
        thinking_supported=False,
        default_temp=0.2,
        open="moonshot",
        driver="OpenAIModelDriver",
    ),
}
