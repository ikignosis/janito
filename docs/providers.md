# Supported Providers

Janito supports the following LLM providers:

## OpenAI

- **API Key Env Var**: `OPENAI_API_KEY`
- **Base URL**: `https://api.openai.com/v1`
- **Default Model**: `gpt-5`
- **Driver**: `OpenAIModelDriver`

## Anthropic

- **API Key Env Var**: `ANTHROPIC_API_KEY`
- **Base URL**: `https://api.anthropic.com/v1/`
- **Default Model**: `claude-3-7-sonnet-20250219`
- **Driver**: `OpenAIModelDriver` (OpenAI-compatible endpoint)

## Google Gemini

- **API Key Env Var**: `GOOGLE_API_KEY`
- **Base URL**: `https://generativelanguage.googleapis.com/v1beta/openai/`
- **Default Model**: `gemini-2.5-flash`
- **Driver**: `OpenAIModelDriver` (OpenAI-compatible endpoint)

## Mistral

- **API Key Env Var**: `MISTRAL_API_KEY`
- **Base URL**: `https://api.mistral.ai/v1`
- **Default Model**: `mistral-large-latest`
- **Driver**: `OpenAIModelDriver`

## Alibaba Qwen

- **API Key Env Var**: `ALIBABA_API_KEY`
- **Base URL**: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`
- **Default Model**: `qwen3-next-80b-a3b-instruct`
- **Driver**: `OpenAIModelDriver`

## DeepSeek

- **API Key Env Var**: `DEEPSEEK_API_KEY`
- **Base URL**: `https://api.deepseek.com/v1`
- **Default Model**: `deepseek-chat`
- **Driver**: `OpenAIModelDriver`

## Moonshot

- **API Key Env Var**: `MOONSHOT_API_KEY`
- **Base URL**: `https://api.moonshot.ai/v1`
- **Default Model**: `kimi-k2-0905-preview`
- **Driver**: `OpenAIModelDriver`

## IBM WatsonX

- **API Key Env Var**: `WATSONX_API_KEY`
- **Project ID Env Var**: `WATSONX_PROJECT_ID`
- **Space ID Env Var**: `WATSONX_SPACE_ID`
- **Base URL**: `https://us-south.ml.cloud.ibm.com`
- **Default Model**: `ibm/granite-3-3-8b-instruct`
- **Driver**: `OpenAIModelDriver`

## MiniMax

- **API Key Env Var**: `MINIMAX_API_KEY`
- **Base URL**: `https://api.minimax.io/v1`
- **Default Model**: `minimax-m2.1`
- **Driver**: `OpenAIModelDriver`

## Azure OpenAI

- **API Key Env Var**: `AZURE_OPENAI_API_KEY`
- **Deployment Name Config**: `azure_deployment_name`
- **Base URL**: Provider-specific (configured via deployment)
- **Default Model**: `azure_openai_deployment`
- **Driver**: `AzureOpenAIModelDriver`

> **Note**: For Azure OpenAI, you must specify your deployment name using `--model YOUR_DEPLOYMENT_NAME` or set it in config with `janito set-config azure_deployment_name=your-deployment-name`.

For detailed model specifications per provider, see [Supported Models](models/supported_models.md).