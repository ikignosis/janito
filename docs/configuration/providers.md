# Providers

janito supports multiple AI providers. This guide covers configuration for each.

janito talks to models through **two kinds of API**:

- **OpenAI-compatible APIs** — the `Responses` and `Completions` API types,
  driven by the `openai` package. This is the default for OpenAI and for any
  provider or local server (LM Studio, Ollama, the `custom` provider) that
  exposes an OpenAI-compatible endpoint.
- **Native APIs** — the providers' official SDKs, selectable through API
  types such as `Anthropic` (native Anthropic SDK) and `DashScope` (native
  DashScope SDK). These talk directly to the provider's native API instead of
  its OpenAI-compatible gateway.

The API type is selected per provider with `--set api-type=...` (see the
[`Anthropic`](#native-anthropic-sdk-optional) and
[`DashScope`](#native-dashscope-sdk-optional) sections below).

## Supported Providers

| Provider | Description |
|----------|-------------|
| `openai` | OpenAI API |
| `custom` | Any OpenAI-compatible API (local servers, third-party) |
| `alibaba` | Alibaba Cloud DashScope (Qwen models) |
| `deepseek` | DeepSeek |
| `minimax` | MiniMax AI (MiniMax models) |
| `xiaomi` | Xiaomi AI (Mimo models) |
| `moonshot` | Moonshot AI (Kimi models) |
| `zai` | Z.AI (GLM models) |
| `xai` | xAI (Grok models) |
| `anthropic` | Anthropic (Claude models) |

!!! note
    The provider name is always validated against this list. Whenever you pass
    `--provider <name>` (or set `provider=<name>` in the config), janito checks
    that it is a supported provider — one that maps to an API base URL — and
    rejects unknown names with an error enumerating the supported providers.

## Listing providers

`janito --show-providers` prints every supported provider with its built-in
defaults — default model, API types (the first one is the default), effective
endpoint, masked API key, thinking/reasoning defaults and token limits —
followed by the registered [provider variants](variants.md), each marked with
its base provider. The configured default provider is flagged `[active]`:

```bash
janito --show-providers
```

```
Supported Providers (10):
============================================================
  openai [active]
    Model:         gpt-5.6-luna (default)
    API types:     Responses (default), Completions
    Endpoint:      default OpenAI (no custom base URL)
    API key:       (not set)
    Thinking:      disabled
    Max tokens:    1,050,000 in / 128,000 out
  ...
  alibaba-tokenplan (variant of alibaba)
    Model:         qwen-plus (configured; default qwen3.8-max)
    ...
```

Configured per-provider overrides (e.g. a variant's model or endpoint) are
shown where set, so you can see at a glance which providers are configured
and which still need a key or an endpoint.

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

> API keys are stored in `~/.janito/auth.json`; the model is stored in
> `~/.janito/config.json`. janito does not read `OPENAI_*` environment
> variables. See [Configuration Priority](index.md#configuration-priority).

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

### Reasoning Level

The default model `qwen3.8-max` supports configurable reasoning depth via the
OpenAI-compatible `reasoning_effort` parameter. The built-in default is
`xhigh`; the supported levels are `low`, `medium` and `xhigh`.

```bash
# Override the reasoning depth for a single call
janito --reasoning-level medium "Your prompt"

# Set a per-provider default in the config
janito --provider alibaba --set reasoning-level=medium
```

Resolution order: `--reasoning-level` > per-provider config value
(`--set reasoning-level=...`) > built-in default (`xhigh`).

### Thinking Mode

Qwen models reason by default, so thinking mode is enabled out of the box for
the `alibaba` provider: every call sends
`extra_body={'enable_thinking': True}`. Pass `-t` / `--thinking` to force it
on for any provider.

### API Type

The `alibaba` provider defaults to the Chat Completions API: its built-in
default model `qwen3.8-max` is not yet supported by DashScope's `/responses`
endpoint, which rejects it with `Unsupported model: 'qwen3.8-max'.`. The
Responses API is available for models the endpoint supports (e.g. `qwen3.7-max`,
`qwen3.6-plus`, `qwen3.5-plus`, `qwen-plus`, `qwen-flash`); select it with:

```bash
# Per provider (persisted)
janito --provider alibaba --set api-type=Responses

# Per call
janito --provider alibaba --api-type responses --model qwen3.7-max "Your prompt"
```

### Native DashScope SDK (optional)

By default the `alibaba` provider talks to DashScope's OpenAI-compatible
endpoint through the **Chat Completions** API. A **native DashScope SDK** API
type (`DashScope`) is also available: it uses the official `dashscope` Python
package against the DashScope native API (`https://dashscope-intl.aliyuncs.com/api/v1`,
per-API-type endpoint, see `endpoint_by_api_type`).

The `dashscope` package is **optional**; janito aborts the change (with a
message naming the package) if you try to select the `DashScope` API type
without it:

```bash
# Install the optional package first
pip install dashscope

# Then select the native SDK API type
janito --provider alibaba --set api-type=DashScope

# Per call
janito --provider alibaba --api-type DashScope "Explain quantum computing"
```

Thinking mode is enabled out of the box here too: the native SDK receives
`enable_thinking=True` (Qwen models reason by default). The `dashscope`
package does not use `reasoning_effort`, so `--reasoning-level` is accepted
for parity but not mapped to a DashScope parameter.

The DashScope native API serves models from two generation endpoints:
`text-generation` for plain-text models (`qwen-plus`, `qwen-flash`, ...) and
`multimodal-generation` for multimodal models (Qwen-VL / Qwen-Omni, the
`qwen3.x-plus` generation, and the default model `qwen3.8-max`). janito picks
the endpoint from the model name automatically and, if the API ever rejects
the model for that endpoint (`InvalidParameter: url error, please check
url`), retries once on the other endpoint — so the default `qwen3.8-max`
model works out of the box here too.

### Example

```bash
# Step 1: Set provider and model
janito --set provider=alibaba --set model=qwen-plus
# Step 2: Store API key
janito --set-api-key="your-dashscope-api-key" --provider alibaba
# Step 3: Run prompt
janito "Explain quantum computing"
```

## DeepSeek

Use DeepSeek models.

> **Get an API key:** Visit [DeepSeek Platform](https://platform.deepseek.com/) to create an account and generate an API key.

### Configuration

```bash
# Step 1: Set provider and model
janito --set provider=deepseek --set model=deepseek-v4-flash
# Step 2: Store API key
janito --set-api-key="your-deepseek-api-key" --provider deepseek
```

### API Types and Base URLs

The `deepseek` provider supports the OpenAI-compatible **Responses** and
**Completions** API types (Responses is the built-in default) against the
OpenAI-compatible base URL `https://api.deepseek.com`, plus a native
**Anthropic** SDK API type against DeepSeek's Anthropic-compatible base URL
`https://api.deepseek.com/anthropic` (per-API-type endpoint, see
`endpoint_by_api_type`).

The `anthropic` package is **optional**; janito aborts the change (with a
message naming the package) if you try to select the `Anthropic` API type
without it:

```bash
# Install the optional package first
pip install anthropic

# Then select the native Anthropic SDK API type
janito --provider deepseek --set api-type=Anthropic

# Per call
janito --provider deepseek --api-type Anthropic "Explain quantum computing"
```

### Reasoning Level

The default model `deepseek-v4-flash` supports configurable reasoning depth via
the OpenAI-compatible `reasoning_effort` parameter. The supported levels are
`low`, `high` and `max` (the API's default is `high`; `medium`/`xhigh` are
mapped to `high` for compatibility, and `deepseek-v4-pro` currently supports
only `high`/`max`).

```bash
# Override the reasoning depth for a single call
janito --reasoning-level max "Your prompt"

# Set a per-provider default in the config
janito --provider deepseek --set reasoning-level=high
```

Resolution order: `--reasoning-level` > per-provider config value
(`--set reasoning-level=...`) > built-in default (none: the API's own default
`high` applies).

### Thinking Mode

DeepSeek models reason by default, so thinking mode is enabled out of the box
for the `deepseek` provider: every call sends
`extra_body={'enable_thinking': True}`. Pass `-t` / `--thinking` to force it
on for any provider.

### Example

```bash
# Step 1: Set provider and model
janito --set provider=deepseek --set model=deepseek-v4-flash
# Step 2: Store API key
janito --set-api-key="your-deepseek-api-key" --provider deepseek
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

### Reasoning Level

The default model `kimi-k3-256k` supports configurable reasoning depth via the
OpenAI-compatible `reasoning_effort` parameter. The supported levels are
`low`, `high` and `max`, and the built-in default is `max` (the API's own
default).

```bash
# Override the reasoning depth for a single call
janito --reasoning-level low "Your prompt"

# Set a per-provider default in the config
janito --provider moonshot --set reasoning-level=high
```

Resolution order: `--reasoning-level` > per-provider config value
(`--set reasoning-level=...`) > built-in default (`max`).

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

## xAI (Grok)

Use xAI to access Grok models.

> **Get an API key:** Visit [xAI Console](https://console.x.ai/) to create an account and generate an API key.

### Configuration

```bash
# Step 1: Set provider and model
janito --set provider=xai --set model=grok-4
# Step 2: Store API key
janito --set-api-key="your-xai-api-key" --provider xai
```

### Popular Models

| Model | Description |
|-------|-------------|
| `grok-4` | Latest flagship model |
| `grok-3` | High-capability model |
| `grok-2` | Balanced performance model |

### Example

```bash
# Step 1: Set provider and model
janito --set provider=xai --set model=grok-4
# Step 2: Store API key
janito --set-api-key="your-xai-api-key" --provider xai
# Step 3: Run prompt
janito "Explain quantum computing"
```

## Anthropic (Claude)

Use Anthropic to access Claude models through their OpenAI-compatible API.

> **Get an API key:** Visit [Anthropic Console](https://console.anthropic.com/) to create an account and generate an API key.

### Configuration

```bash
# Step 1: Set provider and model
janito --set provider=anthropic --set model=claude-sonnet-5
# Step 2: Store API key
janito --set-api-key="your-anthropic-api-key" --provider anthropic
```

### Popular Models

| Model | Description |
|-------|-------------|
| `claude-sonnet-5` | Latest flagship model (200K context) |
| `claude-opus-4-1` | Highest capability model (200K context) |
| `claude-haiku-4-5` | Fast, cost-effective model (200K context) |

### Native Anthropic SDK (optional)

By default the `anthropic` provider talks to Anthropic's OpenAI-compatible
endpoint (`https://api.anthropic.com/v1/`) through the **Chat Completions**
API. A **native Anthropic SDK** API type (`Anthropic`) is also available: it
uses the official `anthropic` Python package against
`https://api.anthropic.com` (per-API-type endpoint, see
`endpoint_by_api_type`).

The `anthropic` package is **optional**; janito aborts the change (with a
message naming the package) if you try to select the `Anthropic` API type
without it:

```bash
# Install the optional package first
pip install anthropic

# Then select the native SDK API type
janito --provider anthropic --set api-type=Anthropic

# Per call
janito --provider anthropic --api-type Anthropic "Explain quantum computing"
```

### Example

```bash
# Step 1: Set provider and model
janito --set provider=anthropic --set model=claude-sonnet-5
# Step 2: Store API key
janito --set-api-key="your-anthropic-api-key" --provider anthropic
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
