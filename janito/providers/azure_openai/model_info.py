from janito.llm.model import LLMModelInfo
from janito.providers.openai.model_info import MODEL_SPECS as OPENAI_MODEL_SPECS

DEFAULT_MODEL = "azure_openai_deployment"

MODEL_SPECS = {
    "azure_openai_deployment": LLMModelInfo(
        name="azure_openai_deployment",
        context=OPENAI_MODEL_SPECS["gpt-4o"].context,
        max_input=OPENAI_MODEL_SPECS["gpt-4o"].max_input,
        max_cot=OPENAI_MODEL_SPECS["gpt-4o"].max_cot,
        max_response=OPENAI_MODEL_SPECS["gpt-4o"].max_response,
        thinking_supported=OPENAI_MODEL_SPECS["gpt-4o"].thinking_supported,
        default_temp=OPENAI_MODEL_SPECS["gpt-4o"].default_temp,
        open="azure_openai",
        driver="AzureOpenAIModelDriver",
    )
}
