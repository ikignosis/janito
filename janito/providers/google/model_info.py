from janito.llm.model import LLMModelInfo

DEFAULT_MODEL = "gemini-2.5-flash"

MODEL_SPECS = {
    "gemini-2.5-flash": LLMModelInfo(
        name="gemini-2.5-flash",
        other={"description": "Google Gemini 2.5 Flash (OpenAI-compatible endpoint)"},
        open="google",
        driver="OpenAIModelDriver",
        max_response=8192,
        max_cot=24576,
        thinking_supported=True,
    ),
    "gemini-2.5-pro": LLMModelInfo(
        name="gemini-2.5-pro",
        other={"description": "Google Gemini 2.5 Pro (OpenAI-compatible endpoint)"},
        open="google",
        driver="OpenAIModelDriver",
        max_response=65536,
        max_cot=196608,
        thinking_supported=True,
    ),
    "gemini-2.5-flash-lite-preview-06-17": LLMModelInfo(
        name="gemini-2.5-flash-lite-preview-06-17",
        other={
            "description": "Google Gemini 2.5 Flash-Lite Preview (OpenAI-compatible endpoint)"
        },
        open="google",
        driver="OpenAIModelDriver",
        max_response=64000,
        max_cot=192000,
        thinking_supported=True,
    ),
    # Add more Gemini models as needed
}
