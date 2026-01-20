"""Tests for DirectExecutor and OllamaClient."""

import pytest
from unittest.mock import patch, Mock, MagicMock
from oneshot.providers.direct_executor import DirectExecutor
from oneshot.providers.ollama_client import OllamaClient, OllamaResponse


class TestOllamaClient:
    """Test OllamaClient functionality."""

    def test_init_default(self):
        """Test default initialization."""
        client = OllamaClient()
        assert client.base_url == "http://localhost:11434"
        assert client.timeout == 300

    def test_init_custom(self):
        """Test custom initialization."""
        client = OllamaClient(base_url="http://custom:8080", timeout=60)
        assert client.base_url == "http://custom:8080"
        assert client.timeout == 60

    @patch('requests.Session.post')
    def test_generate_success(self, mock_post):
        """Test successful generation."""
        # Mock response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'response': 'Test response',
            'done': True,
            'total_duration': 1000,
            'load_duration': 500,
            'prompt_eval_count': 10,
            'eval_count': 20,
            'eval_duration': 800
        }
        mock_post.return_value = mock_response

        client = OllamaClient()
        result = client.generate("llama-pro:latest", "test prompt")

        assert isinstance(result, OllamaResponse)
        assert result.response == "Test response"
        assert result.done is True
        assert result.total_duration == 1000

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs['json']['model'] == "llama-pro:latest"
        assert kwargs['json']['prompt'] == "test prompt"
        assert kwargs['json']['stream'] is False

    @patch('requests.Session.post')
    def test_generate_request_exception(self, mock_post):
        """Test request exception handling."""
        mock_post.side_effect = Exception("Connection failed")

        client = OllamaClient()
        with pytest.raises(Exception, match="Connection failed"):
            client.generate("model", "prompt")

    @patch('requests.Session.post')
    def test_generate_invalid_json(self, mock_post):
        """Test invalid JSON response handling."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response

        client = OllamaClient()
        # ValueError from json() is not caught by the specific exception handler
        # so it should propagate as-is
        with pytest.raises(ValueError, match="Invalid JSON"):
            client.generate("model", "prompt")

    @patch('requests.Session.get')
    def test_list_models_success(self, mock_get):
        """Test successful model listing."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'models': [
                {'name': 'llama-pro:latest'},
                {'name': 'codellama:7b'}
            ]
        }
        mock_get.return_value = mock_response

        client = OllamaClient()
        models = client.list_models()

        assert models == ['llama-pro:latest', 'codellama:7b']
        mock_get.assert_called_once_with("http://localhost:11434/api/tags", timeout=300)

    @patch('requests.Session.get')
    def test_list_models_exception(self, mock_get):
        """Test model listing exception."""
        import requests
        mock_get.side_effect = requests.RequestException("Connection failed")

        client = OllamaClient()
        with pytest.raises(requests.RequestException, match="Failed to list Ollama models"):
            client.list_models()

    @patch('oneshot.providers.ollama_client.OllamaClient.list_models')
    def test_check_connection_success(self, mock_list):
        """Test successful connection check."""
        mock_list.return_value = ['model1', 'model2']

        client = OllamaClient()
        assert client.check_connection() is True
        mock_list.assert_called_once()

    @patch('oneshot.providers.ollama_client.OllamaClient.list_models')
    def test_check_connection_failure(self, mock_list):
        """Test failed connection check."""
        mock_list.side_effect = Exception("Connection failed")

        client = OllamaClient()
        assert client.check_connection() is False

    def test_repr(self):
        """Test string representation."""
        client = OllamaClient(base_url="http://test:8080", timeout=60)
        assert repr(client) == "OllamaClient(base_url=http://test:8080, timeout=60)"


class TestDirectExecutor:
    """Test DirectExecutor functionality."""

    def test_init_default(self):
        """Test default initialization."""
        with patch('oneshot.providers.direct_executor.OllamaClient') as mock_client:
            executor = DirectExecutor()
            assert executor.model == "llama-pro:latest"
            assert executor.base_url == "http://localhost:11434"
            assert executor.timeout == 300
            mock_client.assert_called_once_with(base_url="http://localhost:11434", timeout=300)

    def test_init_custom(self):
        """Test custom initialization."""
        with patch('oneshot.providers.direct_executor.OllamaClient') as mock_client:
            executor = DirectExecutor(
                model="custom-model",
                base_url="http://custom:8080",
                timeout=60
            )
            assert executor.model == "custom-model"
            assert executor.base_url == "http://custom:8080"
            assert executor.timeout == 60
            mock_client.assert_called_once_with(base_url="http://custom:8080", timeout=60)

    def test_run_task_success(self):
        """Test successful task execution."""
        with patch('oneshot.providers.direct_executor.OllamaClient') as mock_client_class:
            mock_client = Mock()
            mock_client.check_connection.return_value = True
            mock_client.generate.return_value = OllamaResponse(
                response="42",
                done=True,
                total_duration=1000,
                load_duration=500,
                prompt_eval_count=5,
                eval_count=10,
                eval_duration=800
            )
            mock_client_class.return_value = mock_client

            executor = DirectExecutor()
            result = executor.run_task("What is 2+2?")

            assert result.success is True
            assert result.output == "42"
            assert result.error is None
            assert result.metadata['provider'] == 'direct'
            assert result.metadata['model'] == 'llama-pro:latest'
            assert result.metadata['total_duration'] == 1000

            mock_client.check_connection.assert_called_once()
            mock_client.generate.assert_called_once_with(
                model="llama-pro:latest",
                prompt="What is 2+2?",
                stream=False
            )

    def test_run_task_connection_failure(self):
        """Test connection failure handling."""
        with patch('oneshot.providers.direct_executor.OllamaClient') as mock_client_class:
            mock_client = Mock()
            mock_client.check_connection.return_value = False
            mock_client_class.return_value = mock_client

            executor = DirectExecutor()
            result = executor.run_task("test prompt")

            assert result.success is False
            assert result.output == ''
            assert "Cannot connect to Ollama service" in result.error
            assert result.metadata['provider'] == 'direct'

    def test_run_task_incomplete_response(self):
        """Test incomplete response handling."""
        with patch('oneshot.providers.direct_executor.OllamaClient') as mock_client_class:
            mock_client = Mock()
            mock_client.check_connection.return_value = True
            mock_client.generate.return_value = OllamaResponse(
                response="partial",
                done=False
            )
            mock_client_class.return_value = mock_client

            executor = DirectExecutor()
            result = executor.run_task("test prompt")

            assert result.success is False
            assert result.output == ''
            assert "incomplete or failed" in result.error

    def test_run_task_exception_handling(self):
        """Test exception handling during execution."""
        with patch('oneshot.providers.direct_executor.OllamaClient') as mock_client_class:
            mock_client = Mock()
            mock_client.check_connection.return_value = True
            mock_client.generate.side_effect = Exception("API Error")
            mock_client_class.return_value = mock_client

            executor = DirectExecutor()
            result = executor.run_task("test prompt")

            assert result.success is False
            assert result.output == ''
            assert "Direct executor failed: API Error" in result.error
            assert result.metadata['exception_type'] == 'Exception'

    def test_repr(self):
        """Test string representation."""
        with patch('oneshot.providers.direct_executor.OllamaClient'):
            executor = DirectExecutor(
                model="test-model",
                base_url="http://test:8080",
                timeout=60
            )
            expected = "DirectExecutor(model=test-model, base_url=http://test:8080, timeout=60)"
            assert repr(executor) == expected