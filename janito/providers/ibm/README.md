# IBM WatsonX AI Provider

This provider enables access to IBM WatsonX AI services, including IBM's Granite models and other hosted models.

## Setup

### Prerequisites

1. **IBM Cloud Account**: You need an IBM Cloud account with WatsonX AI service enabled.
2. **API Key**: Generate an API key from your IBM Cloud dashboard.
3. **Project ID**: Create a WatsonX project and get the project ID.

### Authentication

Set up your credentials using the CLI:

```bash
# Set the API key
janito --set-api-key YOUR_IBM_API_KEY -p ibm

# Set the project ID
janito --set-config ibm project_id YOUR_PROJECT_ID

# Optional: Set space ID if using WatsonX spaces
janito --set-config ibm space_id YOUR_SPACE_ID
```

### Environment Variables

Alternatively, you can set environment variables:

```bash
export WATSONX_API_KEY="your-api-key"
export WATSONX_PROJECT_ID="your-project-id"
export WATSONX_SPACE_ID="your-space-id"  # optional
```

## Available Models

The IBM provider supports the following models:

- **ibm/granite-3-8b-instruct**: IBM's Granite 3 8B Instruct model (default)
- **ibm/granite-3-2b-instruct**: IBM's Granite 3 2B Instruct model
- **meta-llama/llama-3-1-8b-instruct**: Meta Llama 3.1 8B hosted on WatsonX
- **meta-llama/llama-3-1-70b-instruct**: Meta Llama 3.1 70B hosted on WatsonX
- **mistralai/mistral-large**: Mistral Large model hosted on WatsonX

## Usage

### Command Line

```bash
# Use IBM provider with default model
janito -p ibm "Explain quantum computing"

# Use specific IBM model
janito -p ibm -m ibm/granite-3-2b-instruct "Generate a Python function"

# Interactive chat mode
janito -p ibm --chat
```

### Configuration

You can set IBM as your default provider:

```bash
janito --set-config provider ibm
```

## API Reference

The IBM provider uses IBM WatsonX's REST API with OpenAI-compatible format. The base URL is:

```
https://us-south.ml.cloud.ibm.com
```

## Limitations

- **Rate Limits**: IBM WatsonX has rate limits based on your subscription tier
- **Context Window**: Models have different context window limits (typically 128K tokens)
- **Region Support**: Currently configured for US-South region

## Troubleshooting

### Common Issues

1. **Authentication Error**: Ensure your API key and project ID are correct
2. **Model Not Found**: Check if the model is available in your WatsonX project
3. **Rate Limit Exceeded**: Wait and retry, or upgrade your subscription

### Debug Mode

Enable debug logging to see API requests:

```bash
janito -p ibm --verbose "Your prompt here"
```