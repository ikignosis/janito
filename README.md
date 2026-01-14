# Janito CLI

A powerful command-line tool for running LLM-powered workflows with built-in tool execution capabilities.

## Quick Start

### Installation

```bash
uv pip install janito
```

### First-Time Setup

1. **Get your API key**: Sign up at [Moonshot AI](https://platform.moonshot.cn/) and get your API key
2. **Set your API key**:
   ```bash
   janito --set-api-key YOUR_MOONSHOT_API_KEY -p moonshot
   ```

### Basic Usage

**Moonshot (Recommended - Default Provider)**
```bash
# Using the default provider
janito "Create a Python script that reads a CSV file"

# Using a specific Moonshot model
janito -m kimi-k2-thinking "Explain quantum computing"
```

**Other Providers**
```bash
# OpenAI
janito -p openai -m gpt-4 "Write a React component"

# Anthropic
janito -p anthropic -m claude-sonnet-4-5-20250929 "Analyze this code"

# Google
janito -p google -m gemini-2.0-flash-exp "Generate unit tests"
```

### Interactive Chat Mode

By default, running `janito` without any arguments starts an interactive chat session:
```bash
janito
```

In chat mode, you can:

- Have multi-turn conversations
- Execute code and commands

- **One-shot mode**: Pass a prompt directly for single tasks:
```bash
janito "Create a Python script that reads a CSV file"
```

### Available Commands

- `janito --list-providers` - List all supported providers
- `janito --list-models` - List all available models
- `janito --list-tools` - List all available tools
- `janito --show-config` - Show current configuration

### Configuration

Set default provider and model:
```bash
janito --set provider=moonshot
janito --set model=kimi-k2-thinking
```

## Providers

### Moonshot (Recommended)

- **Models**: kimi-k2-turbo-preview, kimi-k2-thinking, kimi-k2-0905-preview
- **Strengths**: Excellent Chinese/English support, competitive pricing, fast responses
- **Setup**: Get API key from [Moonshot AI Platform](https://platform.moonshot.ai/)

### OpenAI

- **Models**: gpt-5, gpt-4.1, gpt-4o, gpt-4-turbo, gpt-3.5-turbo
- **Setup**: Get API key from [OpenAI Platform](https://platform.openai.com/)

### Anthropic

- **Models**: claude-3-7-sonnet-20250219, claude-3-5-sonnet-20241022, claude-3-opus-20250514
- **Setup**: Get API key from [Anthropic Console](https://console.anthropic.com/)

### IBM WatsonX

- **Models**: ibm/granite-3-8b-instruct, ibm/granite-3-2b-instruct, meta-llama/llama-3-1-8b-instruct, meta-llama/llama-3-1-70b-instruct, mistralai/mistral-large
- **Strengths**: Enterprise-grade AI, IBM Granite models, hosted Llama and Mistral models
- **Setup**: Get API key and project ID from [IBM Cloud](https://cloud.ibm.com/)

### Google

- **Models**: gemini-2.5-flash, gemini-2.5-pro, gemini-2.5-flash-lite-preview-06-17
- **Setup**: Get API key from [Google AI Studio](https://makersuite.google.com/)

## Advanced Features

### Tool Usage

Janito includes powerful built-in tools for:

- File operations (read, write, search)
- Code execution
- Web scraping
- System commands
- And more...

### Profiles
Use predefined system prompts:
```bash
janito --developer "Create a REST API"  # Same as --profile developer
janito --market "Analyze market trends"   # Same as --profile market-analyst
```

### Environment Variables

> **Note**: API keys are set via `janito --set-api-key YOUR_KEY -p PROVIDER` and stored in `~/.janito/auth.json`. Provider-specific API key environment variables are not supported.

The following environment variables are supported:

| Variable | Description |
|----------|-------------|
| `BASE_URL` | Custom API base URL (overrides provider default) |

## Examples

### Code Generation
```bash
janito "Create a Python FastAPI application with user authentication"
```

### File Analysis
```bash
janito "Analyze the performance bottlenecks in my_app.py"
```

### Data Processing
```bash
janito "Process this CSV file and generate summary statistics"
```

### Web Development
```bash
janito "Create a responsive landing page with Tailwind CSS"
```

## Support

- **Full Documentation**: https://ikignosis.org/janito/
- **Issues**: Report bugs and feature requests on GitHub
- **Discord**: Join our community for help and discussions