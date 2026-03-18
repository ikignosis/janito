"""
Provider configuration management for Janito CLI.

Handles provider-specific settings including base URLs for API endpoints.

Provider Base URLs:
{
    "minimax": "https://api.minimax.io/v1",
    "openai": None,  # Standard OpenAI - no base_url needed
    "anthropic": "https://api.anthropic.com/v1",
    # ... more providers
}
"""

from typing import Dict, Optional


# Provider to Base URL mapping
# None means the standard OpenAI API endpoint (no custom base URL needed)
PROVIDER_BASE_URLS: Dict[str, Optional[str]] = {
    # AI Providers with OpenAI-compatible APIs
    "minimax": "https://api.minimax.io/v1",
    "openai": None,  # Standard OpenAI - uses default endpoint
    "anthropic": "https://api.anthropic.com/v1",
    "azure": None,  # Azure requires explicit endpoint configuration
    "groq": "https://api.groq.com/openai/v1",
    "groqcloud": "https://api.groq.com/openai/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "mistral": "https://api.mistral.ai/v1",
    "cohere": "https://api.cohere.ai/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
    "anyscale": "https://api.endpoints.anyscale.com/v1",
    "together": "https://api.together.xyz/v1",
    "perplexity": "https://api.perplexity.ai",
    "novita": "https://api.novita.ai/v1",
    "localai": "http://localhost:8080/v1",  # LocalAI default
    "ollama": "http://localhost:11434/v1",  # Ollama with OpenAI compat
    "lmstudio": "http://localhost:1234/v1",  # LM Studio with OpenAI compat
    "ollama3": "http://localhost:8000/v1",  # Ollama3 with OpenAI compat
    "vllm": "http://localhost:8000/v1",  # vLLM with OpenAI compat
    "textsynth": "https://api.textsynth.com/v1",
    "alibaba": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "baichuan": "https://api.baichuan-ai.com/v1",
    "tencent": "https://hunyuan.cloud.tencent.com/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v1",
    "moonshot": "https://api.moonshot.cn/v1",
    "StepFun": "https://api.stepfun.com/v1",
    "01ai": "https://api.01.ai/v1",
    "siliconflow": "https://api.siliconflow.cn/v1",
}


def get_base_url_from_provider(provider: str) -> Optional[str]:
    """
    Get the base URL for a given provider name.
    
    Args:
        provider: The provider name (case-insensitive)
    
    Returns:
        The base URL if found, None otherwise
    """
    if not provider:
        return None
    
    # Try exact match first, then case-insensitive
    if provider in PROVIDER_BASE_URLS:
        return PROVIDER_BASE_URLS[provider]
    
    # Try case-insensitive match
    provider_lower = provider.lower()
    for key, value in PROVIDER_BASE_URLS.items():
        if key.lower() == provider_lower:
            return value
    
    return None


def list_supported_providers() -> list:
    """
    List all supported providers.
    
    Returns:
        List of provider names
    """
    return list(PROVIDER_BASE_URLS.keys())
