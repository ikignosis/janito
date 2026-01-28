# Supported LLM Models

This document lists all supported large language models (LLMs) across providers, as defined in the codebase.

## OpenAI

| Model Name | Context Window | Max Response | Thinking Supported |
|------------|----------------|--------------|--------------------|
| `gpt-3.5-turbo` | 16,385 | 4,096 | No |
| `gpt-4.1` | 1,047,576 | 32,768 | No |
| `gpt-4.1-mini` | 1,047,576 | 32,768 | No |
| `gpt-4.1-nano` | 1,047,576 | 32,768 | No |
| `gpt-4-turbo` | 128,000 | N/A | No |
| `gpt-4o` | 128,000 | 4,096 | No |
| `gpt-4o-mini` | 128,000 | 16,384 | No |
| `o3-mini` | 200,000 | 100,000 | Yes |
| `o3` | 200,000 | 100,000 | Yes |
| `o4-mini` | 200,000 | 100,000 | Yes |
| `gpt-5` | 200,000 | 100,000 | Yes |
| `gpt-5-mini` | 200,000 | 100,000 | Yes |
| `gpt-5-nano` | 200,000 | 100,000 | Yes |

> **Note**: `gpt-4-turbo-alt` is a duplicate entry for internal use and should not be selected by users.

## Anthropic

| Model Name | Max Response | Thinking Supported |
|------------|--------------|--------------------|
| `claude-opus-4-20250514` | 32,000 | No |
| `claude-sonnet-4-20250514` | 64,000 | No |
| `claude-3-7-sonnet-20250219` | 64,000 | No |
| `claude-3-5-haiku-20241022` | 8,192 | No |
| `claude-3-5-sonnet-20241022` | 8,192 | No |
| `claude-3-haiku-20240307` | 4,096 | No |

## Google Gemini

| Model Name | Max Response | Max COT | Thinking Supported |
|------------|--------------|---------|--------------------|
| `gemini-2.5-flash` | 8,192 | 24,576 | Yes |
| `gemini-2.5-pro` | 65,536 | 196,608 | Yes |
| `gemini-2.5-flash-lite-preview-06-17` | 64,000 | 192,000 | Yes |

## Mistral

| Model Name | Context Window | Max Input | Max Response | Thinking Supported |
|------------|----------------|-----------|--------------|--------------------|
| `codestral-latest` | 256,000 | 250,000 | 4,096 | No |
| `codestral-2405` | 256,000 | 250,000 | 4,096 | No |
| `mistral-small-latest` | 32,000 | 28,000 | 4,096 | No |
| `mistral-medium-latest` | 32,000 | 28,000 | 4,096 | No |
| `mistral-large-latest` | 128,000 | 120,000 | 4,096 | No |
| `devstral-small-latest` | 128,000 | 120,000 | 4,096 | No |
| `devstral-medium-latest` | 128,000 | 120,000 | 4,096 | No |

## Cerebras

| Model Name | Max Input | Max Response | Description |
|------------|-----------|--------------|-------------|
| `qwen-3-32b` | 128,000 | 16,384 | Qwen 3 32B model for general instruction following |
| `qwen-3-235b-a22b-instruct-2507` | 128,000 | 16,384 | Qwen 3 235B A22B instruction-tuned model (preview) |
| `qwen-3-235b-a22b-thinking-2507` | 128,000 | 16,384 | Qwen 3 235B A22B thinking model for reasoning tasks (preview) |
| `qwen-3-coder-480b` | 128,000 | 16,384 | Qwen 3 Coder 480B model for programming tasks (preview) |
| `gpt-oss-120b` | 128,000 | 16,384 | GPT-OSS 120B open-source model (preview) |

## Z.AI

| Model Name | Context Window | Max Input | Max COT | Max Response | Thinking Supported | Supports Tools | Supports Images |
|------------|----------------|-----------|---------|--------------|--------------------|----------------|-----------------|
| `glm-4.5` | 128,000 | 128,000 | 4,096 | 4,096 | Yes | Yes | Yes |
| `glm-4.5-air` | 128,000 | 128,000 | 4,096 | 4,096 | Yes | Yes | Yes |
| `glm-4.6` | 128,000 | 128,000 | 4,096 | 4,096 | Yes | Yes | Yes |

## Alibaba Qwen

| Model Name | Context Window | Max Response | Category |
|------------|----------------|--------------|----------|
| `qwen-turbo` | 1,008,192 | 8,192 | Alibaba Qwen Turbo Model (OpenAI-compatible) |
| `qwen-plus` | 131,072 | 8,192 | Alibaba Qwen Plus Model (OpenAI-compatible) |
| `qwen-flash` | 1,000,000 | 8,192 | Alibaba Qwen Flash Model (OpenAI-compatible) |
| `qwen-max` | 32,768 | 8,192 | Alibaba Qwen Max Model (OpenAI-compatible) |
| `qwen3-coder-plus` | 1,048,576 | 65,536 | Alibaba Qwen3 Coder Plus Model (OpenAI-compatible) |
| `qwen3-coder-480b-a35b-instruct` | 262,144 | 65,536 | Alibaba Qwen3 Coder 480B A35B Instruct Model (OpenAI-compatible) |
| `qwen3-235b-a22b-thinking-2507` | 131,072 | 32,768 | Alibaba Qwen3 235B A22B Thinking Model (OpenAI-compatible) |
| `qwen3-235b-a22b-instruct-2507` | 129,024 | 32,768 | Alibaba Qwen3 235B A22B Instruct Model (OpenAI-compatible) |
| `qwen3-30b-a3b-thinking-2507` | 126,976 | 32,768 | Alibaba Qwen3 30B A3B Thinking Model (OpenAI-compatible) |
| `qwen3-30b-a3b-instruct-2507` | 129,024 | 32,768 | Alibaba Qwen3 30B A3B Instruct Model (OpenAI-compatible) |
| `qwen3-next-80b-a3b-instruct` | 262,144 | 65,536 | Alibaba Qwen3-Max Preview (256K) - 80B A3B Instruct Model (OpenAI-compatible) |
| `qwen3-next-80b-a3b-thinking` | 262,144 | 65,536 | Alibaba Qwen3-Max Preview (256K) - 80B A3B Thinking Model (OpenAI-compatible) |
| `qwen3-max` | 262,144 | 65,536 | Alibaba Qwen3-Max Preview (256K) - Standard Model (OpenAI-compatible) |
| `qwen3-max-2026-01-23` | 262,144 | 65,536 | Alibaba Qwen3-Max-Thinking Latest - Advanced reasoning with adaptive tool use (OpenAI-compatible) |

## DeepSeek

| Model Name | Context Window | Max Tokens | Description |
|------------|----------------|------------|-------------|
| `deepseek-chat` | 131,072 | 4,096 | DeepSeek Chat Model (OpenAI-compatible) |
| `deepseek-reasoner` | 131,072 | 32,768 | DeepSeek Reasoner Model (OpenAI-compatible) |

## Moonshot

| Model Name | Context Window | Max Input | Max Response | Thinking Supported |
|------------|----------------|-----------|--------------|--------------------|
| `kimi-k2-turbo-preview` | 128,000 | 100,000 | 4,096 | No |
| `kimi-k2-thinking` | 256,000 | 200,000 | 8,192 | Yes |
| `kimi-k2-0905-preview` | 128,000 | 100,000 | 4,096 | No |

## IBM WatsonX

| Model Name | Context Window | Max Input | Max Response | Max COT | Thinking Supported |
|------------|----------------|-----------|--------------|---------|--------------------|
| `openai/gpt-oss-120b` | 128,000 | 128,000 | 4,096 | 4,096 | Yes |
| `ibm/granite-3-8b-instruct` | 128,000 | 128,000 | 4,096 | 4,096 | No |
| `ibm/granite-3-3-8b-instruct` | 128,000 | 128,000 | 4,096 | 4,096 | No |
| `meta-llama/llama-3-1-70b-instruct` | 128,000 | 128,000 | 4,096 | 4,096 | No |
| `meta-llama/llama-3-3-70b-instruct` | 128,000 | 128,000 | 4,096 | 4,096 | No |
| `mistralai/mistral-large` | 128,000 | 128,000 | 4,096 | 4,096 | No |
| `mistralai/mistral-large-2407` | 128,000 | 128,000 | 4,096 | 4,096 | No |
| `openai/gpt-oss-20b` | 128,000 | 128,000 | 4,096 | 4,096 | Yes |

## Azure OpenAI

Azure OpenAI supports any deployment name configured by the user. The following are known model mappings:

| Model Name | Mapped To | Context Window | Max Response |
|------------|-----------|----------------|--------------|
| `azure_openai_deployment` | gpt-4o | 128,000 | 4,096 |

> **Note**: Azure OpenAI deployments are user-defined. Use `--provider azure_openai --model YOUR_DEPLOYMENT_NAME` to use any valid deployment.

 

*Last updated from source code: September 2025*
