from janito.llm.model import LLMModelInfo

DEFAULT_MODEL = "minimax-m2.1"

MODEL_SPECS = {
    "minimax-m2.1": LLMModelInfo(
        name="minimax-m2.1",
        max_response=128000,
        default_temp=0.7,
        driver="OpenAIModelDriver",
    ),
    "minimax-m2.1-lightning": LLMModelInfo(
        name="minimax-m2.1-lightning",
        max_response=128000,
        default_temp=0.7,
        driver="OpenAIModelDriver",
    ),
    "minimax-m2": LLMModelInfo(
        name="minimax-m2",
        max_response=128000,
        default_temp=0.7,
        driver="OpenAIModelDriver",
    ),
}
