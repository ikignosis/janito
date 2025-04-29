"""Providers module: defines LLM provider interfaces and implementations."""

from abc import ABC, abstractmethod


class Provider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def create_client(self):
        """Instantiate and return the provider-specific client."""
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """Return the default model for this provider."""
        pass


class OpenAIProvider(Provider):
    def create_client(self):
        from openai import OpenAI

        return OpenAI(
            base_url=self.config.get("base_url", "https://api.openai.com/v1"),
            api_key=self.config["api_key"],
        )

    def get_default_model(self) -> str:
        return self.config.get("default_model", "gpt-3.5-turbo")


class AzureAIProvider(Provider):
    def create_client(self):
        from openai import AzureOpenAI

        return AzureOpenAI(
            api_key=self.config["api_key"],
            azure_endpoint=self.config["base_url"],
            api_version=self.config.get("api_version", "2023-05-15"),
        )

    def get_default_model(self) -> str:
        return self.config.get("default_model", "gpt-35-turbo")


class OpenrouterAIProvider(Provider):
    def create_client(self):
        from openai import OpenAI

        return OpenAI(
            base_url=self.config.get("base_url", "https://openrouter.ai/api/v1"),
            api_key=self.config["api_key"],
        )

    def get_default_model(self) -> str:
        return self.config.get("default_model", "openrouter/cognitive")


class FireworksAIProvider(Provider):
    def create_client(self):
        from openai import OpenAI

        return OpenAI(
            base_url=self.config.get(
                "base_url", "https://api.fireworks.ai/inference/v1"
            ),
            api_key=self.config["api_key"],
        )

    def get_default_model(self) -> str:
        return self.config.get(
            "default_model", "accounts/fireworks/models/firefunction-v1"
        )
