# Janito CLI

A powerful command-line tool for running LLM-powered workflows with built-in tool execution capabilities.

## Quick Start

### Installation

```bash
pip install janito
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
# Using the default provider (moonshot) and model
janito "Create a Python script that reads a CSV file"

# Using a specific Moonshot model
janito -m kimi-k1-8k "Explain quantum computing"
```

**Other Providers**
```bash
# OpenAI
janito -p openai -m gpt-4 "Write a React component"

# Anthropic
janito -p anthropic -m claude-3-5-sonnet-20241022 "Analyze this code"

# Google
janito -p google -m gemini-2.0-flash-exp "Generate unit tests"
```

### Interactive Chat Mode

Start an interactive session (default mode):
```bash
janito
```

Or explicitly:
```bash
janito --chat
```

In chat mode, you can:

- Have multi-turn conversations
- Execute code and commands
- Read and write files
- Use built-in tools

### Available Commands

- `janito --list-providers` - List all supported providers
- `janito --list-models` - List all available models
- `janito --list-tools` - List available tools
- `janito --show-config` - Show current configuration

### Configuration

Set default provider and model:
```bash
janito --set provider=moonshot
janito --set model=kimi-k1-8k
```

## Providers

### Moonshot (Recommended)

- **Models**: kimi-k1-8k, kimi-k1-32k, kimi-k1-128k, kimi-k2-turbo-preview
- **Strengths**: Excellent Chinese/English support, competitive pricing, fast responses
- **Setup**: Get API key from [Moonshot AI Platform](https://platform.moonshot.cn/)

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

### 🚀 New in v3.1.0: Enter Key Cancellation
**Chat Mode Enhancement**: Press **Enter** at any time to instantly cancel long-running requests in interactive chat mode. No more waiting for stuck requests!

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
You can also configure via environment variables:

**Moonshot:**
```bash
export MOONSHOT_API_KEY=your_key_here
export JANITO_PROVIDER=moonshot
export JANITO_MODEL=kimi-k1-8k
```

**OpenAI:**
```bash
export OPENAI_API_KEY=your_key_here
export JANITO_PROVIDER=openai
export JANITO_MODEL=gpt-5
```

**IBM WatsonX:**
```bash
export WATSONX_API_KEY=your_key_here
export WATSONX_PROJECT_ID=your_project_id
export WATSONX_SPACE_ID=your_space_id  # optional
export JANITO_PROVIDER=ibm
export JANITO_MODEL=ibm/granite-3-8b-instruct
```

**Anthropic:**
```bash
export ANTHROPIC_API_KEY=your_key_here
export JANITO_PROVIDER=anthropic
export JANITO_MODEL=claude-3-7-sonnet-20250219
```

**Google:**
```bash
export GOOGLE_API_KEY=your_key_here
export JANITO_PROVIDER=google
export JANITO_MODEL=gemini-2.5-flash
```

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

- **Documentation**: Check individual provider directories for detailed setup guides
- **Issues**: Report bugs and feature requests on GitHub
- **Discord**: Join our community for help and discussions