# Mistral Setup Guide

This guide walks you through setting up Mistral AI models with Janito.

## Overview

Mistral AI provides a comprehensive suite of models including:
- **General-purpose models**: Mistral Small, Medium, and Large
- **Code-focused models**: Codestral for code generation and completion
- **Development-focused models**: Devstral for agentic software development

## Prerequisites

1. **Python 3.8+** installed
2. **Janito** installed (`pip install janito`)
3. **Mistral API Key** from [La Plateforme](https://console.mistral.ai/)

## Quick Setup

### 1. Get Your API Key

1. Visit [Mistral AI La Plateforme](https://console.mistral.ai/)
2. Sign up or log in to your account
3. Navigate to **API Keys** section
4. Create a new API key
5. Copy the key for use in Janito

### 2. Configure Janito

Set your Mistral API key using one of these methods:

#### Method 1: Environment Variable (Recommended)

```bash
# Linux/macOS
export MISTRAL_API_KEY="your-api-key-here"

# Windows (PowerShell)
$env:MISTRAL_API_KEY="your-api-key-here"

# Windows (Command Prompt)
set MISTRAL_API_KEY=your-api-key-here
```

#### Method 2: Janito CLI

```bash
janito set-api-key mistral your-api-key-here
```

#### Method 3: Interactive Setup

```bash
janito chat
# Then use the !model command to select mistral and follow prompts
```

## Available Models

### General Purpose Models
- **mistral-large-latest** (default) - Most capable with 128k context
- **mistral-medium-latest** - Balanced performance with 32k context
- **mistral-small-latest** - Compact and efficient with 32k context

### Code-Focused Models
- **codestral-latest** - Specialized for code generation with 256k context
- **codestral-2405** - Previous version of code-focused model

### Development-Focused Models
- **devstral-small-latest** - Optimized for agentic tool use
- **devstral-medium-latest** - Enhanced agentic capabilities

## Usage Examples

### Basic Chat

```bash
# Start chat with default model (mistral-large-latest)
janito chat --provider mistral

# Use specific model
janito chat --provider mistral --model codestral-latest
```

### Single-Shot Mode

```bash
# Quick question
janito "Explain quantum computing" --provider mistral

# Code generation
janito "Write a Python function for fibonacci" --provider mistral --model codestral-latest
```

### Configuration File

You can also configure Mistral in your Janito configuration:

```yaml
# ~/.janito/config.yaml
providers:
  mistral:
    api_key: "your-api-key-here"
    model: "mistral-large-latest"
```

## Model Selection Tips

- **General conversations**: Use `mistral-large-latest` for best results
- **Code generation**: Use `codestral-latest` for programming tasks
- **Development workflows**: Use `devstral-*` models for agentic development
- **Cost optimization**: Use `mistral-small-latest` for simpler tasks

## Troubleshooting

### Common Issues

1. **"Invalid API key" error**
   - Verify your API key is correct
   - Check if the key has proper permissions
   - Ensure no extra spaces in the key

2. **"Model not found" error**
   - Check available models with: `janito list-models --provider mistral`
   - Ensure you're using the exact model name

3. **Rate limiting**
   - Mistral has rate limits based on your plan
   - Consider upgrading your plan or implementing retry logic

### Debug Mode

Enable debug logging to see API requests:

```bash
# Enable HTTP debug for Mistral
export MISTRAL_DEBUG_HTTP=1
janito chat --provider mistral --verbose-api
```

### Testing Connection

Test your setup:

```bash
# Ping the provider
janito ping-providers

# List available models
janito list-models --provider mistral

# Test with a simple query
janito "Hello, Mistral!" --provider mistral
```

## Advanced Configuration

### Custom Base URL

If you need to use a different endpoint (e.g., for enterprise deployments):

```bash
janito set-config mistral.base_url "https://your-custom-endpoint.com/v1"
```

### Model Parameters

You can set default parameters for Mistral models:

```bash
janito set-config mistral.temperature 0.5
janito set-config mistral.max_tokens 2000
```

## Support

For additional help:
- Check the [Mistral AI documentation](https://docs.mistral.ai/)
- Review [Janito troubleshooting guides](guides/configuration.md)
- Join our [Discord community](https://discord.gg/janito)