# Together AI Setup Guide

This guide explains how to set up the Together AI provider for Janito, giving you access to OLMo 2 models and other open-source models.

## 1. Get Your Together AI API Key

1. Visit [Together AI](https://api.together.xyz/)
2. Sign up for an account
3. Navigate to your API keys section
4. Copy your API key

## 2. Configure Janito for Together AI

### Set your API key:
```bash
janito --set-api-key YOUR_TOGETHER_API_KEY --provider together
```

### Set Together AI as your default provider:
```bash
janito --set-config provider together
```

## 3. Available Models

The Together AI provider supports several models including:

- **allenai/OLMo-2-0325-32B-Instruct** (default) - Fully open 32B parameter model
- **allenai/OLMo-2-1124-7B-Instruct** - 7B parameter OLMo 2 model
- **allenai/OLMo-2-0425-1B** - 1B parameter OLMo 2 model
- **meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo**
- **meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo**
- **mistralai/Mixtral-8x7B-Instruct-v0.1**
- **deepseek-ai/deepseek-llm-67b-chat**

## 4. Usage Examples

### Basic chat:
```bash
janito chat --provider together
```

### Use a specific model:
```bash
janito chat --provider together --model allenai/OLMo-2-1124-7B-Instruct
```

### Single query:
```bash
janito "Explain quantum computing" --provider together
```

### Use OLMo 2 1B for faster responses:
```bash
janito "Write a Python function" --provider together --model allenai/OLMo-2-0425-1B
```

## 5. Environment Variables

The Together AI provider uses the following environment variable:
- `TOGETHER_API_KEY` - Your Together AI API key

## 6. Troubleshooting

### Check if Together AI is available:
```bash
janito --list-providers
```

### Verify your API key:
```bash
janito ping-providers
```

### List available models:
```bash
janito list-models --provider together
```

## 7. Pricing

Together AI offers pay-as-you-go pricing. Check their [pricing page](https://api.together.xyz/pricing) for current rates.

## 8. Regional Availability

Together AI is available globally, including Europe and China, with no regional restrictions.