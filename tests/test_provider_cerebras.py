"""Tests for Cerebras provider."""

import os
import pytest
from unittest.mock import patch, MagicMock

from janito.providers.cerebras.provider import CerebrasProvider
from janito.providers.cerebras.model_info import MODEL_SPECS


class TestCerebrasProvider:
    """Test cases for Cerebras provider."""

    def test_provider_initialization(self):
        """Test provider initialization with default config."""
        provider = CerebrasProvider()
        assert provider.name == "cerebras"
        assert provider.DEFAULT_MODEL == "llama-4-scout-17b-16e-instruct"
        assert provider.MAINTAINER == "Cerebras Systems"

    def test_provider_initialization_with_config(self):
        """Test provider initialization with custom config."""
        config = {"model": "llama-4-maverick-17b-128e-instruct", "temperature": 0.5}
        provider = CerebrasProvider(config=config)
        assert provider.config["model"] == "llama-4-maverick-17b-128e-instruct"
        assert provider.config["temperature"] == 0.5

    def test_get_model_info_all_models(self):
        """Test getting info for all models."""
        provider = CerebrasProvider()
        model_info = provider.get_model_info()
        assert isinstance(model_info, dict)
        assert len(model_info) == len(MODEL_SPECS)
        assert "llama-4-scout-17b-16e-instruct" in model_info
        assert "llama-4-maverick-17b-128e-instruct" in model_info

    def test_get_model_info_single_model(self):
        """Test getting info for a specific model."""
        provider = CerebrasProvider()
        model_info = provider.get_model_info("llama-4-scout-17b-16e-instruct")
        assert isinstance(model_info, dict)
        assert model_info["name"] == "llama-4-scout-17b-16e-instruct"
        assert model_info["driver"] == "CerebrasModelDriver"

    def test_get_model_info_invalid_model(self):
        """Test getting info for invalid model."""
        provider = CerebrasProvider()
        model_info = provider.get_model_info("invalid-model")
        assert model_info is None

    def test_is_model_available(self):
        """Test model availability check."""
        provider = CerebrasProvider()
        assert provider.is_model_available("llama-4-scout-17b-16e-instruct")
        assert provider.is_model_available("llama-4-maverick-17b-128e-instruct")
        assert not provider.is_model_available("invalid-model")

    @patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"})
    def test_create_driver_with_env_key(self):
        """Test creating driver with API key from environment."""
        provider = CerebrasProvider()
        driver = provider.create_driver()
        assert driver.api_key == "test-key"
        assert driver.model == "llama-4-scout-17b-16e-instruct"

    def test_create_driver_with_config_key(self):
        """Test creating driver with API key from config."""
        config = {"api_key": "config-key", "model": "llama-3.3-70b-instruct"}
        provider = CerebrasProvider(config=config)
        driver = provider.create_driver()
        assert driver.api_key == "config-key"
        assert driver.model == "llama-3.3-70b-instruct"

    def test_create_driver_missing_api_key(self):
        """Test creating driver without API key raises error."""
        provider = CerebrasProvider()
        with pytest.raises(ValueError, match="Cerebras API key is required"):
            provider.create_driver()

    def test_create_driver_invalid_model(self):
        """Test creating driver with invalid model raises error."""
        config = {"api_key": "test-key", "model": "invalid-model"}
        provider = CerebrasProvider(config=config)
        with pytest.raises(ValueError, match="Model 'invalid-model' is not supported"):
            provider.create_driver()

    def test_driver_property(self):
        """Test driver property returns driver instance."""
        with patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key"}):
            provider = CerebrasProvider()
            driver = provider.driver
            assert driver is not None
            assert hasattr(driver, "chat_complete")
