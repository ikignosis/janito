# MiniMax Setup

To use MiniMax models with Janito, follow these steps:

## 1. Get Your API Key

1. Sign up at [https://platform.minimax.io/](https://platform.minimax.io/)
2. Navigate to your API keys page
3. Create a new API key or copy an existing one

## 2. Set the API Key

Set your MiniMax API key using the CLI:

```bash
janito set-api-key --provider minimax --key YOUR_API_KEY_HERE
```

Or set it as an environment variable:

```bash
export MINIMAX_API_KEY="YOUR_API_KEY_HERE"
```

## 3. Available Models

Janito supports the following MiniMax models:

- `minimax-m2.1` - Latest model with 230B total parameters (10B activated per inference), optimized for code generation and refactoring with polyglot code mastery and enhanced reasoning
- `minimax-m2.1-lightning` - Same performance as M2.1 with significantly faster inference and low latency
- `minimax-m2` - Previous generation model with 200k context length, 128k max output, agentic capabilities, function calling, and advanced reasoning

## 4. Usage Examples

### List available models

```bash
janito list-models --provider minimax
```

### Use a specific model

```bash
janito chat --provider minimax --model minimax-m2.1
```

### Set as default provider

```bash
janito set-config provider=minimax
```

## Notes

- MiniMax is accessed through an OpenAI-compatible API endpoint at `https://api.minimax.io/v1`
- The default model is `minimax-m2.1`
- All models support streaming responses
- M2.1 models support up to 128k context window
- M2.1 is optimized for coding, tool use, instruction following, and long-horizon planning
- M2.1 excels in multilingual scenarios and matches or exceeds Claude Sonnet 4.5 performance

For more information, visit the [MiniMax documentation](https://platform.minimax.io/).
