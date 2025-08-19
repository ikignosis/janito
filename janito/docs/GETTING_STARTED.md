# Getting Started with Janito

This guide will help you set up Janito CLI quickly and start using it with your preferred AI provider.

## Quick Setup (2 minutes)

### 1. Install Janito
```bash
pip install janito
```

### 2. Choose Your Provider

Janito supports multiple AI providers. Choose one to get started:

**Moonshot (Recommended for Chinese users)**
1. Go to [Moonshot AI Platform](https://platform.moonshot.cn/)
2. Sign up for an account
3. Navigate to API Keys section
4. Create a new API key

**OpenAI**
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up and add payment method
3. Create an API key

**IBM WatsonX**
1. Go to [IBM Cloud](https://cloud.ibm.com/)
2. Create a WatsonX AI service
3. Get your API key and project ID

### 3. Configure Janito

**Moonshot Setup:**
```bash
# Set Moonshot as your default provider
janito --set-api-key YOUR_API_KEY -p moonshot

# Verify it's working
janito "Hello, can you introduce yourself?"
```

**OpenAI Setup:**
```bash
# Set OpenAI as your default provider
janito --set-api-key YOUR_OPENAI_API_KEY -p openai

# Verify it's working
janito "Hello, can you introduce yourself?"
```

**IBM WatsonX Setup:**
```bash
# Set IBM WatsonX as your default provider
janito --set-api-key YOUR_WATSONX_API_KEY -p ibm
janito --set-config ibm project_id YOUR_PROJECT_ID

# Verify it's working
janito "Hello, can you introduce yourself?"
```

## Your First Commands

### Basic Usage
```bash
# Simple prompt
janito "Create a Python script to calculate fibonacci numbers"

# With specific model
janito -m kimi-k1-8k "Explain machine learning in simple terms"

# Interactive chat mode
janito --chat
```

### Working with Files
```bash
# Analyze a file
janito "Analyze the performance of my_app.py" < my_app.py

# Generate code in a specific directory
janito -W ./my_project "Create a REST API with FastAPI"
```

## Configuration Options

### Set as Default Provider
```bash
# Make your chosen provider the permanent default
janito --set provider=moonshot  # or openai, ibm, etc.
janito --set model=kimi-k1-8k     # or gpt-5, ibm/granite-3-8b-instruct, etc.
```

### Environment Variables
You can also use environment variables:

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
export JANITO_MODEL=ibm/granite-3-3-8b-instruct
```

## Available Models by Provider

### Moonshot Models
- **kimi-k1-8k**: Fast responses, good for general tasks
- **kimi-k1-32k**: Better for longer contexts
- **kimi-k1-128k**: Best for very long documents
- **kimi-k2-turbo-preview**: Latest model with enhanced capabilities
- **kimi-k2-turbo-preview**: Turbo version of the advanced reasoning model

### OpenAI Models
- **gpt-5**: Latest GPT model with advanced capabilities
- **gpt-4.1**: High-performance model for complex tasks
- **gpt-4o**: Optimized for speed and cost
- **o3-mini**: Reasoning-focused model

### IBM WatsonX Models
- **ibm/granite-3-3-8b-instruct**: IBM's latest Granite 3.3 8B Instruct model (default)
- **ibm/granite-3-8b-instruct**: IBM's Granite 3 8B Instruct model
- **meta-llama/llama-3-3-70b-instruct**: Meta Llama 3.3 70B hosted on WatsonX
- **meta-llama/llama-3-1-70b-instruct**: Meta Llama 3.1 70B hosted on WatsonX
- **mistralai/mistral-large-2407**: Latest Mistral Large model hosted on WatsonX

## Next Steps

1. **Explore tools**: Run `janito --list-tools` to see available tools
2. **Try chat mode**: Run `janito --chat` for interactive sessions
3. **Check examples**: Look at the main README.md for more usage examples
4. **Join community**: Get help and share tips with other users

## Troubleshooting

### Common Issues

**"Provider not found" error**
```bash
# Check available providers
janito --list-providers

# Re-register your provider
janito --set-api-key YOUR_KEY -p YOUR_PROVIDER
```

**"Model not available" error**
```bash
# List available models for your provider
janito -p YOUR_PROVIDER --list-models
```

**API key issues**
```bash
# Check current configuration
janito --show-config

# Reset API key
janito --set-api-key NEW_KEY -p YOUR_PROVIDER
```

**IBM WatsonX specific issues**
```bash
# Check if project ID is set
janito --show-config

# Set project ID if missing
janito --set-config ibm project_id YOUR_PROJECT_ID
```

### Getting Help

- Check the main README.md for comprehensive documentation
- Use `janito --help` for command-line options
- Visit our GitHub repository for issues and discussions