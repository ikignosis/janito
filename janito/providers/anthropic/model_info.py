from janito.llm.model import LLMModelInfo

MODEL_SPECS = {
    "claude-sonnet-4-5-20250929": LLMModelInfo(
        name="claude-sonnet-4-5-20250929",
        max_response=64000,
        default_temp=0.7,
        driver="OpenAIModelDriver",
    ),
    "claude-opus-4-1-20250805": LLMModelInfo(
        name="claude-opus-4-1-20250805",
        max_response=32000,
        default_temp=0.7,
        driver="OpenAIModelDriver",
    ),
    "claude-opus-4-20250514": LLMModelInfo(
        name="claude-opus-4-20250514",
        max_response=32000,
        default_temp=0.7,
        driver="OpenAIModelDriver",
    ),
    "claude-sonnet-4-20250514": LLMModelInfo(
        name="claude-sonnet-4-20250514",
        max_response=64000,
        default_temp=0.7,
        driver="OpenAIModelDriver",
    ),
    "claude-3-7-sonnet-20250219": LLMModelInfo(
        name="claude-3-7-sonnet-20250219",
        max_response=64000,
        default_temp=0.7,
        driver="OpenAIModelDriver",
    ),
    "claude-3-5-haiku-20241022": LLMModelInfo(
        name="claude-3-5-haiku-20241022",
        max_response=8192,
        default_temp=0.7,
        driver="OpenAIModelDriver",
    ),
    "claude-3-5-sonnet-20241022": LLMModelInfo(
        name="claude-3-5-sonnet-20241022",
        max_response=8192,
        default_temp=0.7,
        driver="OpenAIModelDriver",
    ),
    "claude-3-haiku-20240307": LLMModelInfo(
        name="claude-3-haiku-20240307",
        max_response=4096,
        default_temp=0.7,
        driver="OpenAIModelDriver",
    ),
}
