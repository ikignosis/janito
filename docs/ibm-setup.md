# IBM WatsonX Setup Guide

This guide walks you through setting up IBM WatsonX as your AI provider in Janito.

## Prerequisites

Before you begin, you'll need:

1. **IBM Cloud Account**: Create an account at [IBM Cloud](https://cloud.ibm.com)
2. **WatsonX AI Service**: Enable the WatsonX AI service in your IBM Cloud account
3. **Project Setup**: Create a WatsonX project to get your project ID

## Step 1: Get Your API Key

1. Log in to [IBM Cloud](https://cloud.ibm.com)
2. Go to **Manage > Access (IAM) > API keys**
3. Click **Create an IBM Cloud API key**
4. Give it a name (e.g., "janito-watsonx")
5. Copy the API key - you'll need it for configuration

## Step 2: Create a WatsonX Project

1. Go to [WatsonX](https://dataplatform.cloud.ibm.com/wx)
2. Click **Create project**
3. Choose **Data science** project type
4. Give your project a name and description
5. Once created, copy the **Project ID** from the project settings

## Step 3: Configure Janito

### Using the CLI

Set up your IBM WatsonX credentials:

```bash
# Set your IBM API key
janito --set-api-key YOUR_IBM_API_KEY -p ibm

# Set your WatsonX project ID
janito --set-config ibm project_id YOUR_PROJECT_ID

# Optional: Set space ID if using WatsonX spaces
janito --set-config ibm space_id YOUR_SPACE_ID
```

### Using Environment Variables

Alternatively, you can set environment variables:

```bash
export WATSONX_API_KEY="your-api-key"
export WATSONX_PROJECT_ID="your-project-id"
export WATSONX_SPACE_ID="your-space-id"  # optional
```

## Step 4: Test Your Setup

Verify your IBM WatsonX setup is working:

```bash
# Test with a simple prompt
janito -p ibm "Hello, how are you?"

# Use a specific model
janito -p ibm -m ibm/granite-3-8b-instruct "Explain quantum computing"

# Start interactive chat
janito -p ibm --chat
```

## Available Models

IBM WatsonX provides several models through Janito:

- **openai/gpt-oss-120b** (default) - Open-source 120B model with thinking capabilities
- **openai/gpt-oss-20b** - Open-source 20B model with thinking capabilities
- **ibm/granite-3-8b-instruct** - IBM's Granite 3 8B Instruct model
- **ibm/granite-3-3-8b-instruct** - Updated Granite 3.3 8B Instruct model
- **meta-llama/llama-3-1-70b-instruct** - Meta Llama 3.1 70B
- **meta-llama/llama-3-3-70b-instruct** - Meta Llama 3.3 70B
- **mistralai/mistral-large** - Mistral Large model
- **mistralai/mistral-large-2407** - Mistral Large 2407 version

## Configuration Options

### Set IBM as Default Provider

```bash
janito --set-config provider ibm
```

### Region Configuration

By default, Janito uses the US-South region. You can change this:

```bash
janito --set-config ibm region us-south
# or
janito --set-config ibm region eu-gb
```

### Custom Base URL

If you need to use a custom endpoint:

```bash
janito --set-config ibm base_url https://your-custom-endpoint.com
```

## Troubleshooting

### Common Issues

**Authentication Error**

- Verify your API key is correct
- Ensure your IBM Cloud account has WatsonX AI service enabled
- Check that your project ID is valid

**Model Not Found**

- Ensure the model is available in your WatsonX project
- Check your subscription tier allows access to the model
- Verify the model name is spelled correctly

**Rate Limit Exceeded**

- IBM WatsonX has rate limits based on your subscription tier
- Wait and retry, or consider upgrading your subscription
- Use smaller models for testing to reduce token consumption

### Debug Mode

Enable debug logging to see detailed API requests:

```bash
janito -p ibm --verbose "Your prompt here"
```

### Getting Help

If you continue to have issues:

1. Check the [IBM WatsonX documentation](https://cloud.ibm.com/docs/watsonx)
2. Verify your IBM Cloud account permissions
3. Ensure your WatsonX project is properly configured
4. Contact IBM support for account-specific issues

## Next Steps

- Learn about [using profiles](guides/profiles.md) to manage different configurations
- Explore [advanced prompting techniques](guides/prompting/README.md)
- Check out the [supported models](supported-providers-models.md) for more options