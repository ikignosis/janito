# Supported Providers and Models

> **💡 Quick Tip**: Use the convenient `model@provider` syntax to specify both model and provider in one argument: `janito -m gpt-4@openai "Your prompt"`

This page lists the supported providers and their available models, organized by openness and sorted alphabetically within each category.

> 📋 **Platform & Documentation Access**: For information about which providers have publicly accessible platforms and documentation vs. blocked access, see [Platform & Documentation Access](provider-platform-access.md).

## Open-Source / Open-Weight Models

### Alibaba

- **Qwen3 235B A22B Instruct** (default) - Latest 1M context model
- **Qwen3 235B A22B Thinking** - Reasoning-focused version
- **Qwen3 30B A3B Instruct** - Compact 1M context model
- **Qwen3 30B A3B Thinking** - Compact reasoning version
- **Qwen3 Coder Plus** - Specialized for programming tasks
- **Qwen3 Coder 480B** - Large-scale coding model
- **Qwen Turbo** - High-speed general purpose
- **Qwen Plus** - Balanced performance
- **Qwen Max** - Maximum capability
- **Qwen3-Max-Thinking (2026-01-23)** - Latest flagship reasoning model with adaptive tool use and test-time scaling



### DeepSeek

- **DeepSeek Chat** (default) - General purpose chat model (128K context)
- **DeepSeek Reasoner** - Specialized for complex reasoning tasks (128K context)

### MiniMax

- **MiniMax M2.1** (default) - Latest model with 230B total parameters (10B activated per inference), optimized for code generation and refactoring with polyglot code mastery and enhanced reasoning (128K context)
- **MiniMax M2.1 Lightning** - Same performance as M2.1 with significantly faster inference and low latency (128K context)
- **MiniMax M2** - Previous generation model with 200k context length, 128k max output, agentic capabilities, function calling, and advanced reasoning

MiniMax models are optimized for coding, tool use, instruction following, and long-horizon planning. M2.1 excels in multilingual scenarios and matches or exceeds Claude Sonnet 4.5 performance.

### Mistral

- **Mistral Large Latest** (default) - Most capable Mistral model with 128k context
- **Mistral Medium Latest** - Balanced performance with 32k context
- **Mistral Small Latest** - Compact and efficient with 32k context
- **Codestral Latest** - Specialized for code generation with 256k context
- **Codestral 2405** - Previous version of code-focused model
- **Devstral Small Latest** - Optimized for agentic tool use in software development
- **Devstral Medium Latest** - Enhanced agentic capabilities for development tasks

Mistral provides both general-purpose and specialized models, with Codestral specifically designed for code generation and Devstral for agentic software development.

For setup instructions, see the [Mistral Setup Guide](mistral-setup.md).

### Moonshot

- **Kimi K2 0905 Preview** (default) - Latest generation with enhanced performance
- **Kimi K2 Turbo Preview** - Turbo version with optimized speed
- **Kimi K2 0711 Preview** - Previous preview version

Moonshot provides open-source Kimi models with competitive performance.

### Z.AI

- **GLM-4.5** (default) - Advanced reasoning and conversation
- **GLM-4.5 Air** - Compact and efficient version

### IBM WatsonX

**Open-Source Models:**

- **openai/gpt-oss-120b** (default) - Open-source 120B model with thinking capabilities
- **openai/gpt-oss-20b** - Open-source 20B model with thinking capabilities

**IBM Granite Models:**

- **ibm/granite-3-8b-instruct** - IBM's Granite 3 8B Instruct model with 128K context
- **ibm/granite-3-3-8b-instruct** - Updated Granite 3.3 8B Instruct model

**Hosted Models:**

- **meta-llama/llama-3-1-70b-instruct** - Meta Llama 3.1 70B hosted on WatsonX
- **meta-llama/llama-3-3-70b-instruct** - Meta Llama 3.3 70B hosted on WatsonX
- **mistralai/mistral-large** - Mistral Large model hosted on WatsonX
- **mistralai/mistral-large-2407** - Mistral Large 2407 version

IBM WatsonX provides access to IBM's Granite models as well as popular open-source models hosted on their platform. All models support 128K context windows.

## Proprietary Models

### Anthropic

- **Claude Sonnet 4.5** (default) - Latest model with enhanced agent and coding capabilities
- **Claude Opus 4.1** - Exceptional model for specialized complex tasks
- **Claude Opus 4** - High-capability model for complex tasks
- **Claude Sonnet 4** - Balanced performance and capability
- **Claude 3.7 Sonnet** - High-performance model with extended thinking
- **Claude 3.5 Haiku** - Fast and efficient
- **Claude 3 Haiku** - Compact and cost-effective

### Google

- **Gemini 2.5 Flash** (default) - Fast and efficient
- **Gemini 2.5 Pro** - Advanced capabilities with extended context
- **Gemini 2.5 Flash-Lite Preview** - Lightweight preview version

### OpenAI

- **GPT-5** (default) - Latest generation with advanced reasoning
- **GPT-5 Mini** - Compact version of GPT-5
- **GPT-5 Nano** - Ultra-compact version
- **GPT-4.1** - Enhanced GPT-4 with improved capabilities
- **GPT-4.1-mini** - Balanced performance and efficiency
- **GPT-4.1-nano** - Lightweight version
- **GPT-4 Turbo** - High-performance GPT-4 variant
- **GPT-4o** - Multimodal GPT-4 optimized for chat
- **GPT-4o-mini** - Compact multimodal version
- **o3** - Advanced reasoning model
- **o3-mini** - Compact reasoning model
- **o4-mini** - Latest mini reasoning model
- **GPT-3.5 Turbo** - Cost-effective general purpose

For setup instructions, see the [OpenAI Setup Guide](openai-setup.md).

### Azure OpenAI

- **Azure OpenAI Deployment** - Custom Azure OpenAI deployments

For setup instructions, see [Using Azure OpenAI with Janito](reference/azure-openai.md).
