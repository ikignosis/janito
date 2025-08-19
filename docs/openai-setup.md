# OpenAI Setup Guide

This guide will help you set up Janito to work with OpenAI's models.

## Prerequisites

1. An OpenAI account
2. An API key from OpenAI

## Getting an API Key

1. Go to [OpenAI's API Keys page](https://platform.openai.com/api-keys)
2. Sign in to your OpenAI account
3. Click on "Create new secret key"
4. Copy the generated key and save it in a secure location

## Configuration

You can configure your OpenAI API key in several ways:

### Option 1: Using the CLI

```bash
janito --set-api-key openai YOUR_API_KEY
```

### Option 2: Environment Variable

Set the `OPENAI_API_KEY` environment variable:

```bash
export OPENAI_API_KEY=YOUR_API_KEY
```

On Windows:
```cmd
set OPENAI_API_KEY=YOUR_API_KEY
```

### Option 3: Configuration File

Add the following to your Janito configuration file:

```yaml
providers:
  openai:
    api_key: YOUR_API_KEY
```

## Available Models

Janito supports the following OpenAI models:

- GPT-5 (default)
- GPT-5 Mini
- GPT-5 Nano
- GPT-4
- GPT-4 Turbo
- GPT-3.5 Turbo

## Usage

After configuration, you can use OpenAI models with Janito:

```bash
# Use the default model (GPT-5)
janito "Explain quantum computing"

# Specify a specific model
janito -m gpt-4 "Explain quantum computing"

# Use in chat mode
janito -c

# Use in chat mode with a specific model
janito -c -m gpt-4-turbo
```

## Troubleshooting

If you encounter issues:

1. Verify your API key is correct and active
2. Check that you have sufficient credits in your OpenAI account
3. Ensure your network connection can reach OpenAI's API endpoints