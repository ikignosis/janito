# Provider Platform and Documentation Access

This document categorizes providers based on both platform/documentation accessibility and model quality tiers, helping users make informed decisions about which providers to prioritize.

## High-Quality Models with Full Platform Access

These providers offer premium models with complete platform and documentation accessibility.

| Provider | Platform Access | Documentation | API Docs | Model Quality | Notes |
|----------|-----------------|---------------|----------|---------------|-------|
| **Google** | [AI Studio](https://aistudio.google.com) | [Gemini API Docs](https://ai.google.dev/gemini-api/docs) | [API Reference](https://ai.google.dev/gemini-api/docs) | 🏆 Premium | Gemini 2.5 Pro/Flash - Industry leading |
| **IBM WatsonX** | [IBM Cloud Console](https://cloud.ibm.com) | [WatsonX Docs](https://cloud.ibm.com/docs/watsonx) | [API Reference](https://cloud.ibm.com/apidocs/watsonx-ai) | 🏆 Premium | Granite + hosted Llama/Mistral |
| **Anthropic** | [Console](https://console.anthropic.com) | [API Docs](https://docs.anthropic.com/en/api/getting-started) | [API Reference](https://docs.anthropic.com/en/api/messages) | 🏆 Premium | Claude 3.7 Sonnet - Top reasoning |

## High-Quality Models with Restricted Access

Premium models but limited platform/documentation access.

| Provider | Platform Access | Documentation | API Docs | Model Quality | Status |
|----------|-----------------|---------------|----------|---------------|--------|
| **OpenAI** | [Platform](https://platform.openai.com) | [API Docs](https://platform.openai.com/docs) | [API Reference](https://platform.openai.com/docs/api-reference) | 🏆 Premium | ❌ All Blocked |
| **DeepSeek** | [Platform](https://platform.deepseek.com) | [API Docs](https://platform.deepseek.com/api-docs) | [API Reference](https://platform.deepseek.com/api-docs) | 🏆 Premium | ❌ All Blocked |

## Quality Open-Source Models with Full Access

Open-source/open-weight models with complete accessibility.

| Provider | Platform Access | Documentation | API Docs | Model Quality | Notes |
|----------|-----------------|---------------|----------|---------------|-------|
| **Alibaba** | [Alibaba Cloud Console](https://account.alibabacloud.com) | [Model Studio Help](https://www.alibabacloud.com/help/en/model-studio) | [API Reference](https://www.alibabacloud.com/help/en/model-studio/api-reference) | 🥇 High | Qwen3 235B - Leading open-source |
| **Cerebras** | [API Dashboard](https://api.cerebras.ai) | [Inference Docs](https://cerebras.ai/inference) | [API Docs](https://cerebras.ai/inference) | 🥇 High | Qwen-3 32B - Fast inference |
| **Moonshot** | [Platform](https://platform.moonshot.ai) | [API Docs](https://platform.moonshot.ai/docs) | [API Reference](https://platform.moonshot.ai/docs) | 🥈 Medium | Kimi K2 - Competitive open-source |
| **Z.ai** | [API Management](https://z.ai/manage-apikey/apikey-list) | [Model API Docs](https://z.ai/model-api) | [API Reference](https://z.ai/model-api) | 🥈 Medium | GLM-4.5 - Solid performance |

## Specialized Models

| Provider | Platform Access | Documentation | API Docs | Model Quality | Specialization |
|----------|-----------------|---------------|----------|---------------|----------------|
| **Mistral** | [Console](https://console.mistral.ai) | [API Docs](https://docs.mistral.ai) | [API Reference](https://docs.mistral.ai/api) | 🥈 Medium | Codestral for code, Devstral for agents |

## Status Legend

### Access Levels

- ✅ **Full Access**: Both platform and documentation are publicly accessible
- ⚠️ **Partial Access**: Documentation available but platform/dashboard blocked
- ❌ **Blocked**: Both platform and documentation are inaccessible (403 errors)

### Model Quality Tiers

- 🏆 **Premium**: Industry-leading proprietary models (GPT-4 class)
- 🥇 **High**: Top-tier open-source models (Qwen-3, Llama-3.3 class)
- 🥈 **Medium**: Solid open-source models with competitive performance

## Usage Recommendations

### For Production Use

1. **Google** or **IBM WatsonX** - Full access + premium models
2. **Alibaba** or **Cerebras** - Full access + high-quality open-source

### For Development/Testing

1. **Alibaba Qwen3** - Best open-source performance
2. **Cerebras** - Fast inference for Qwen-3 models
3. **Moonshot** or **Z.ai** - Good alternatives

### For Specialized Tasks

- **Mistral Codestral** - Code generation
- **Anthropic Claude** - Complex reasoning (if accessible)

## Notes

- **API Endpoints**: All API base URLs return 404 when accessed directly without authentication (expected behavior)
- **Authentication**: All providers require valid API keys for actual API usage
- **Regional Restrictions**: Some providers may have additional access restrictions based on geographic location
- **Azure OpenAI**: Custom deployments available through Azure (see [Azure OpenAI Guide](reference/azure-openai.md))