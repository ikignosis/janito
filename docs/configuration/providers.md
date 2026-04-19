# Providers

janito supports multiple AI providers. This guide covers configuration for each.

## Supported Providers

| Provider | Type | Description |
|----------|------|-------------|
| `openai` | Standard | OpenAI API (default) |
| `custom` | Custom | Any OpenAI-compatible API (local servers, third-party) |
| `alibaba` | Third-party | Alibaba Cloud DashScope (Qwen models) |
| `minimax` | Third-party | MiniMax AI (abab models) |
| `xiaomi` | Third-party | Xiaomi AI (Mimo models) |
| `moonshot` | Third-party | Moonshot AI (Kimi models) |
| `zai` | Third-party | Z.AI (GLM models) |

## OpenAI

### Configuration

```bash
# Step 1: Set provider and model
janito --set provider=openai --set model=gpt-4
# Step 2: Store API key
janito --set-api-key="sk-your-key" --provider openai
```

Or interactively:

```bash
janito --config
```

### Environment Variables

```bash
export OPENAI_API_KEY="sk-your-key"
export OPENAI_MODEL="gpt-4"
```

## Custom Providers (OpenAI-Compatible)

Use any OpenAI-compatible API, including local servers like LM Studio, Ollama, or third-party providers.

### Configuration

```bash
# Step 1: Set provider, endpoint, and model
janito --set provider=custom --set endpoint="http://localhost:8000/v1" --set model="my-model"
# Step 2: Store API key (optional)
janito --set-api-key="optional-key" --provider custom
```

### Common Endpoints

| Provider | Endpoint Example |
|----------|------------------|
| LM Studio | `http://localhost:1234/v1` |
| Ollama | `http://localhost:11434/v1` |
| LocalAI | `http://localhost:8080/v1` |

### Example: LM Studio

```bash
# Step 1: Configure provider
janito --set provider=custom \
        --set endpoint="http://localhost:1234/v1" \
        --set model="local-model-name"
# Step 2: Set placeholder API key
janito --set-api-key="not-needed" --provider custom
# Step 3: Run prompt
janito "Hello"
```

## Alibaba (Qwen)

Use Alibaba Cloud DashScope to access Qwen models.

> **Get an API key:** Visit [Alibaba Cloud Model Studio](https://modelstudio.alibabacloud.com/) to create an account and generate a DashScope API key.

### Configuration

```bash
# Step 1: Set provider and model
janito --set provider=alibaba --set model=qwen-plus
# Step 2: Store API key
janito --set-api-key="your-dashscope-api-key" --provider alibaba
```

### Popular Models

| Model | Description |
|-------|-------------|
| `qwen-plus` | Balanced performance and cost |
| `qwen-max` | Highest capability model |
| `qwen-turbo` | Fast, cost-effective |
| `qwen-long` | Extended context window |

### Example

```bash
# Step 1: Set provider and model
janito --set provider=alibaba --set model=qwen-plus
# Step 2: Store API key
janito --set-api-key="your-dashscope-api-key" --provider alibaba
# Step 3: Run prompt
janito "Explain quantum computing"
```

## MiniMax

Use MiniMax AI to access abab models.

> **Get an API key:** Visit [MiniMax Open Platform](https://platform.minimax.io/) to create an account and generate an API key.

### Configuration

```bash
# Step 1: Set provider and model
janito --set provider=minimax --set model=abab6.5s-chat
# Step 2: Store API key
janito --set-api-key="your-minimax-api-key" --provider minimax
```

### Popular Models

| Model | Description |
|-------|-------------|
| `abab6.5s-chat` | Fast, cost-effective chat model |
| `abab6.5-chat` | Balanced performance model |
| `abab6.5g-chat` | High-quality generation model |

### Example

```bash
# Step 1: Set provider and model
janito --set provider=minimax --set model=abab6.5s-chat
# Step 2: Store API key
janito --set-api-key="your-minimax-api-key" --provider minimax
# Step 3: Run prompt
janito "Explain quantum computing"
```

## Xiaomi (Mimo)

Use Xiaomi AI to access Mimo models.

> **Get an API key:** Visit [XiaoAI Open Platform](https://api.xiaomimimo.com/) to create an account and generate an API key.

### Configuration

```bash
# Step 1: Set provider and model
janito --set provider=xiaomi --set model=mimo-v2
# Step 2: Store API key
janito --set-api-key="your-xiaomi-api-key" --provider xiaomi
```

### Popular Models

| Model | Description |
|-------|-------------|
| `mimo-v2` | Latest Xiaomi language model |
| `mimo-v1` | Previous generation model |

### Example

```bash
# Step 1: Set provider and model
janito --set provider=xiaomi --set model=mimo-v2
# Step 2: Store API key
janito --set-api-key="your-xiaomi-api-key" --provider xiaomi
# Step 3: Run prompt
janito "Explain quantum computing"
```

## Moonshot (Kimi)

Use Moonshot AI to access Kimi models.

> **Get an API key:** Visit [Moonshot AI Open Platform](https://platform.moonshot.cn/) to create an account and generate an API key.

### Configuration

```bash
# Step 1: Set provider and model
janito --set provider=moonshot --set model=moonshot-v1-8k
# Step 2: Store API key
janito --set-api-key="your-moonshot-api-key" --provider moonshot
```

### Popular Models

| Model | Description |
|-------|-------------|
| `moonshot-v1-8k` | Standard model with 8K context |
| `moonshot-v1-32k` | Extended context window (32K) |
| `moonshot-v1-128k` | Long context window (128K) |

### Example

```bash
# Step 1: Set provider and model
janito --set provider=moonshot --set model=moonshot-v1-8k
# Step 2: Store API key
janito --set-api-key="your-moonshot-api-key" --provider moonshot
# Step 3: Run prompt
janito "Explain quantum computing"
```

## Z.AI (GLM)

Use Z.AI to access GLM models (Zhipu AI).

> **Get an API key:** Visit [Z.AI Open Platform](https://open.bigmodel.cn/) to create an account and generate an API key.

### Configuration

```bash
# Step 1: Set provider and model
janito --set provider=zai --set model=glm-4-plus
# Step 2: Store API key
janito --set-api-key="your-zai-api-key" --provider zai
```

### Popular Models

| Model | Description |
|-------|-------------|
| `glm-4-plus` | Enhanced GLM-4 model |
| `glm-4` | Standard GLM-4 model |
| `glm-4-flash` | Fast, cost-effective model |
| `glm-4v-plus` | Vision-language model |

### Example

```bash
# Step 1: Set provider and model
janito --set provider=zai --set model=glm-4-plus
# Step 2: Store API key
janito --set-api-key="your-zai-api-key" --provider zai
# Step 3: Run prompt
janito "Explain quantum computing"
```

## Provider Comparison

| Feature | OpenAI | Custom | Third-Party Providers |
|---------|--------|--------|-----------------------|
| Function Calling | ✅ | Depends on API | Depends on provider |
| Streaming | ✅ | Depends on API | Depends on provider |
| Vision | ✅ | Depends on API | Depends on provider |
| Context Window | Up to 128k | Varies | Varies by model |

## Troubleshooting

### Connection Errors

- Verify the endpoint URL is correct (including `/v1` suffix)
- Check firewall settings
- Ensure the server is running (for local servers)

### Authentication Errors

- Verify your API key is correct
- Check if the API key has the necessary permissions
- Some local servers don't require an API key - try `--set-api-key="not-needed"`
