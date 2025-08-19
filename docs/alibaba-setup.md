# Alibaba Cloud Qwen Setup Guide

This guide explains how to set up the Alibaba Cloud Qwen provider for Janito.

## Prerequisites

- An Alibaba Cloud account
- Access to the Alibaba Cloud Qwen model service
- API key for authentication

## Getting Your API Key

1. Log in to your [Alibaba Cloud account](https://account.alibabacloud.com)
2. Navigate to the **Qwen Model Service** in the console
3. Go to **API Keys** or **Security Settings**
4. Create a new API key or use an existing one
5. Copy the API key value

## Setting Up the API Key

You can set your API key using the Janito CLI:

```bash
janito --set-api-key alibaba:your-api-key-here
```

Alternatively, you can set the environment variable:

```bash
export ALIBABA_API_KEY=your-api-key-here
```

## Configuration

The Alibaba provider uses the following environment variable:

- `ALIBABA_API_KEY`: Your Alibaba Cloud API key

## Available Models

The Alibaba provider supports the following models:

- `qwen-turbo`: Fast, lightweight model for simple tasks
- `qwen-plus`: Balanced performance and capability
- `qwen-max`: Most capable model for complex tasks
- `qwen3-coder-plus`: Coding-focused model with 128k context
- `qwen3-coder-480b-a35b-instruct`: Advanced coding model
- `qwen3-235b-a22b-thinking-2507`: 1M context thinking model
- `qwen3-235b-a22b-instruct-2507`: 1M context instruct model
- `qwen3-30b-a3b-thinking-2507`: 1M context thinking model
- `qwen3-30b-a3b-instruct-2507`: 1M context instruct model

## Default Model

The default model is `qwen3-235b-a22b-instruct-2507`, which provides 129k context and is suitable for general-purpose tasks.

## Troubleshooting

**Q: I'm getting authentication errors**
A: Verify your API key is correct and has the necessary permissions in the Alibaba Cloud console.

**Q: The model is not responding**
A: Check your internet connection and verify the Alibaba Cloud Qwen service is available in your region.

**Q: I want to use a different model**
A: Use the `--model` flag when running Janito:

```bash
janito --provider alibaba --model qwen-max
```
