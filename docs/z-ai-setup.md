# Z.ai API Setup Guide

This guide explains how to set up and use Z.ai's API with your API key.

## Prerequisites

Install the Z.ai SDK package:

```bash
pip install zai-sdk
```

## Getting Your API Key

1. Visit [Z.ai API Management](https://z.ai/manage-apikey/apikey-list)
2. Log in to your Z.ai account
3. Navigate to the API Keys section
4. Create a new API key if you don't have one yet

## API Key Format

Z.ai uses a new key format that includes both a user ID and secret:
```
{id}.{secret}
```

**Important Security Notes:**

- Never share your API keys
- Do not expose keys in browsers or client-side code
- Leaked keys may be automatically regenerated for security
- Store keys securely in environment variables or secure vaults

## Setting Up Your Environment

### Environment Variable (Recommended)

Set your API key as an environment variable:

**Linux/macOS:**
```bash
export ZAI_API_KEY="your-id.your-secret"
```

**Windows (Command Prompt):**
```cmd
set ZAI_API_KEY=your-id.your-secret
```

**Windows (PowerShell):**
```powershell
$env:ZAI_API_KEY="your-id.your-secret"
```

### Configuration File

You can also store your API key in a configuration file (ensure proper file permissions):

```json
{
  "zai_api_key": "your-id.your-secret"
}
```

## Rate Limits and Billing

- Check your [API Management dashboard](https://z.ai/manage-apikey/apikey-list) for current rate limits
- Monitor your usage and billing information
- Contact support for API recharge if needed

## Support

For API-related support:

- Visit [Z.ai Contact](https://z.ai/contact) for product support
- Join the [Discord community](https://z.ai/contact) to chat with developers
- Check the [API documentation](https://z.ai/model-api) for model-specific details

## Available Models

Z.ai provides several models including:

- **GLM-4.5**: Latest flagship model with reasoning, coding, and agent functionalities
- **GLM-4.5-Air**: Lightweight flagship model with cost-effectiveness
- **GLM-4.5-Flash**: Most advanced free model
- **GLM-4-32B-0414-128K**: General-purpose LLM for business and technical domains
- **CogVideoX-3**: Text-to-video model for high-fidelity motion
- **Vidu Q1**: High-fidelity 1080p video generation
- **Vidu 2**: Fast, low-cost 720p video generation

For complete model specifications and capabilities, visit [Z.ai Models](https://z.ai/model-api).