#!/usr/bin/env python3
"""Tests for provider abstraction layer."""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from oneshot.providers import (
    ProviderConfig,
    Provider,
    ExecutorProvider,
    DirectProvider,
    create_provider,
    create_executor_provider,
    create_direct_provider,
)


# ============================================================================
# PROVIDER CONFIG TESTS
# ============================================================================

class TestProviderConfig:
    """Test ProviderConfig validation."""

    def test_executor_config_valid_claude(self):
        """Test valid executor config for claude."""
        config = ProviderConfig(
            provider_type="executor",
            executor="claude",
            model="claude-3-5-haiku-20241022"
        )
        assert config.provider_type == "executor"
        assert config.executor == "claude"
        assert config.model == "claude-3-5-haiku-20241022"

    def test_executor_config_valid_cline(self):
        """Test valid executor config for cline."""
        config = ProviderConfig(
            provider_type="executor",
            executor="cline",
            model=None  # cline doesn't use model
        )
        assert config.provider_type == "executor"
        assert config.executor == "cline"

    def test_executor_config_missing_executor(self):
        """Test that executor config requires executor field."""
        with pytest.raises(ValueError, match="executor provider requires 'executor' field"):
            ProviderConfig(
                provider_type="executor",
                model="some-model"
            )

    def test_executor_config_invalid_executor(self):
        """Test that executor must be claude, cline, aider, or gemini."""
        with pytest.raises(ValueError, match="executor must be 'claude', 'cline', 'aider', or 'gemini'"):
            ProviderConfig(
                provider_type="executor",
                executor="invalid",
                model="some-model"
            )

    def test_executor_config_claude_without_model(self):
        """Test that claude executor allows missing model (uses defaults)."""
        config = ProviderConfig(
            provider_type="executor",
            executor="claude"
        )
        assert config.provider_type == "executor"
        assert config.executor == "claude"
        assert config.model is None  # Model is optional for executors

    def test_direct_config_valid(self):
        """Test valid direct config."""
        config = ProviderConfig(
            provider_type="direct",
            endpoint="http://localhost:11434/v1/chat/completions",
            model="qwen3-8b-coding"
        )
        assert config.provider_type == "direct"
        assert config.endpoint == "http://localhost:11434/v1/chat/completions"
        assert config.model == "qwen3-8b-coding"

    def test_direct_config_with_api_key(self):
        """Test direct config with API key."""
        config = ProviderConfig(
            provider_type="direct",
            endpoint="https://api.openai.com/v1/chat/completions",
            model="gpt-4",
            api_key="sk-test123"
        )
        assert config.api_key == "sk-test123"

    def test_direct_config_missing_endpoint(self):
        """Test that direct config requires endpoint."""
        with pytest.raises(ValueError, match="direct provider requires 'endpoint' field"):
            ProviderConfig(
                provider_type="direct",
                model="some-model"
            )

    def test_direct_config_missing_model(self):
        """Test that direct config requires model."""
        with pytest.raises(ValueError, match="direct provider requires 'model' field"):
            ProviderConfig(
                provider_type="direct",
                endpoint="http://localhost:11434/v1/chat/completions"
            )

    def test_invalid_provider_type(self):
        """Test that provider_type must be executor or direct."""
        with pytest.raises(ValueError, match="provider_type must be 'executor' or 'direct'"):
            ProviderConfig(
                provider_type="invalid"
            )

    def test_custom_timeout(self):
        """Test custom timeout configuration."""
        config = ProviderConfig(
            provider_type="executor",
            executor="claude",
            model="claude-3-5-haiku-20241022",
            timeout=600
        )
        assert config.timeout == 600


# ============================================================================
# EXECUTOR PROVIDER TESTS
# ============================================================================

class TestExecutorProvider:
    """Test ExecutorProvider functionality."""

    def test_executor_provider_creation(self):
        """Test creating an executor provider."""
        config = ProviderConfig(
            provider_type="executor",
            executor="claude",
            model="claude-3-5-haiku-20241022"
        )
        provider = ExecutorProvider(config)
        assert provider.config == config

    @patch('oneshot.oneshot.call_executor')
    def test_executor_provider_generate(self, mock_call_executor):
        """Test ExecutorProvider.generate() calls call_executor."""
        mock_call_executor.return_value = "Test response"

        config = ProviderConfig(
            provider_type="executor",
            executor="claude",
            model="claude-3-5-haiku-20241022",
            timeout=300
        )
        provider = ExecutorProvider(config)

        result = provider.generate("Test prompt")

        assert result == "Test response"
        mock_call_executor.assert_called_once_with(
            prompt="Test prompt",
            model="claude-3-5-haiku-20241022",
            executor="claude",
            initial_timeout=300,
            max_timeout=3600,
            activity_interval=30
        )

    @pytest.mark.asyncio
    @patch('oneshot.oneshot.call_executor_async')
    async def test_executor_provider_generate_async(self, mock_call_executor_async):
        """Test ExecutorProvider.generate_async() calls call_executor_async."""
        mock_call_executor_async.return_value = "Async test response"

        config = ProviderConfig(
            provider_type="executor",
            executor="claude",
            model="claude-3-5-haiku-20241022",
            timeout=300
        )
        provider = ExecutorProvider(config)

        result = await provider.generate_async("Test prompt")

        assert result == "Async test response"
        mock_call_executor_async.assert_called_once_with(
            prompt="Test prompt",
            model="claude-3-5-haiku-20241022",
            executor="claude",
            initial_timeout=300,
            max_timeout=3600,
            activity_interval=30
        )


# ============================================================================
# DIRECT PROVIDER TESTS
# ============================================================================

class TestDirectProvider:
    """Test DirectProvider functionality."""

    def test_direct_provider_creation(self):
        """Test creating a direct provider."""
        config = ProviderConfig(
            provider_type="direct",
            endpoint="http://localhost:11434/v1/chat/completions",
            model="qwen3-8b-coding"
        )
        provider = DirectProvider(config)
        assert provider.config == config

    def test_direct_provider_prepare_request(self):
        """Test request payload preparation."""
        config = ProviderConfig(
            provider_type="direct",
            endpoint="http://localhost:11434/v1/chat/completions",
            model="qwen3-8b-coding"
        )
        provider = DirectProvider(config)

        payload, headers = provider._prepare_request("Test prompt")

        assert payload == {
            "model": "qwen3-8b-coding",
            "messages": [
                {
                    "role": "user",
                    "content": "Test prompt"
                }
            ]
        }
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers

    def test_direct_provider_prepare_request_with_api_key(self):
        """Test request payload with API key."""
        config = ProviderConfig(
            provider_type="direct",
            endpoint="https://api.openai.com/v1/chat/completions",
            model="gpt-4",
            api_key="sk-test123"
        )
        provider = DirectProvider(config)

        payload, headers = provider._prepare_request("Test prompt")

        assert headers["Authorization"] == "Bearer sk-test123"

    def test_direct_provider_extract_response(self):
        """Test extracting response from API response."""
        config = ProviderConfig(
            provider_type="direct",
            endpoint="http://localhost:11434/v1/chat/completions",
            model="qwen3-8b-coding"
        )
        provider = DirectProvider(config)

        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Test response content"
                    }
                }
            ]
        }

        result = provider._extract_response(response_data)
        assert result == "Test response content"

    def test_direct_provider_extract_response_invalid(self):
        """Test error handling for invalid response format."""
        config = ProviderConfig(
            provider_type="direct",
            endpoint="http://localhost:11434/v1/chat/completions",
            model="qwen3-8b-coding"
        )
        provider = DirectProvider(config)

        with pytest.raises(ValueError, match="Invalid API response format"):
            provider._extract_response({})

    def test_direct_provider_generate_success(self):
        """Test successful HTTP request."""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Test response"}}]
            }
            mock_post.return_value = mock_response

            config = ProviderConfig(
                provider_type="direct",
                endpoint="http://localhost:11434/v1/chat/completions",
                model="qwen3-8b-coding",
                timeout=300
            )
            provider = DirectProvider(config)

            result = provider.generate("Test prompt")

            assert result == "Test response"
            mock_post.assert_called_once()

    def test_direct_provider_generate_timeout(self):
        """Test timeout handling."""
        with patch('requests.post') as mock_post:
            import requests
            mock_post.side_effect = requests.exceptions.Timeout()

            config = ProviderConfig(
                provider_type="direct",
                endpoint="http://localhost:11434/v1/chat/completions",
                model="qwen3-8b-coding",
                timeout=300
            )
            provider = DirectProvider(config)

            result = provider.generate("Test prompt")

            assert "ERROR" in result
            assert "timed out" in result

    @pytest.mark.asyncio
    async def test_direct_provider_generate_async_success(self):
        """Test successful async HTTP request."""
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Async test response"}}]
            }

            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            mock_async_client.return_value = mock_client_instance

            config = ProviderConfig(
                provider_type="direct",
                endpoint="http://localhost:11434/v1/chat/completions",
                model="qwen3-8b-coding",
                timeout=300
            )
            provider = DirectProvider(config)

            result = await provider.generate_async("Test prompt")

            assert result == "Async test response"


# ============================================================================
# PROVIDER FACTORY TESTS
# ============================================================================

class TestProviderFactory:
    """Test provider factory functions."""

    def test_create_provider_executor(self):
        """Test factory creates ExecutorProvider."""
        config = ProviderConfig(
            provider_type="executor",
            executor="claude",
            model="claude-3-5-haiku-20241022"
        )
        provider = create_provider(config)
        assert isinstance(provider, ExecutorProvider)

    def test_create_provider_direct(self):
        """Test factory creates DirectProvider."""
        config = ProviderConfig(
            provider_type="direct",
            endpoint="http://localhost:11434/v1/chat/completions",
            model="qwen3-8b-coding"
        )
        provider = create_provider(config)
        assert isinstance(provider, DirectProvider)

    def test_create_executor_provider_helper(self):
        """Test helper function for creating executor provider."""
        provider = create_executor_provider(
            executor="claude",
            model="claude-3-5-haiku-20241022",
            timeout=600
        )
        assert isinstance(provider, ExecutorProvider)
        assert provider.config.executor == "claude"
        assert provider.config.model == "claude-3-5-haiku-20241022"
        assert provider.config.timeout == 600

    def test_create_direct_provider_helper(self):
        """Test helper function for creating direct provider."""
        provider = create_direct_provider(
            endpoint="http://localhost:11434/v1/chat/completions",
            model="qwen3-8b-coding",
            api_key="test-key",
            timeout=600
        )
        assert isinstance(provider, DirectProvider)
        assert provider.config.endpoint == "http://localhost:11434/v1/chat/completions"
        assert provider.config.model == "qwen3-8b-coding"
        assert provider.config.api_key == "test-key"
        assert provider.config.timeout == 600
