"""
Ollama HTTP client for direct executor integration.
"""

import json
import requests
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class OllamaResponse:
    """Response from Ollama API."""
    response: str
    done: bool
    context: Optional[list] = None
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None


class OllamaClient:
    """
    HTTP client for communicating with Ollama API.
    """

    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 300):
        """
        Initialize Ollama client.

        Args:
            base_url (str): Base URL for Ollama API (default: http://localhost:11434)
            timeout (int): Request timeout in seconds (default: 300)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

    def generate(self, model: str, prompt: str, stream: bool = False, **kwargs) -> OllamaResponse:
        """
        Generate a response from Ollama model.

        Args:
            model (str): Model name (e.g., 'llama-pro:latest')
            prompt (str): Input prompt
            stream (bool): Whether to stream the response
            **kwargs: Additional parameters for the API

        Returns:
            OllamaResponse: Parsed response from Ollama

        Raises:
            requests.RequestException: If the HTTP request fails
            ValueError: If the response cannot be parsed
        """
        url = f"{self.base_url}/api/generate"
        data = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            **kwargs
        }

        try:
            response = self.session.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()

            if stream:
                # For streaming, we'd need to handle the stream
                # For now, we'll accumulate the full response
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line.decode('utf-8'))
                        if 'response' in chunk:
                            full_response += chunk['response']
                        if chunk.get('done', False):
                            return OllamaResponse(
                                response=full_response,
                                done=True,
                                context=chunk.get('context'),
                                total_duration=chunk.get('total_duration'),
                                load_duration=chunk.get('load_duration'),
                                prompt_eval_count=chunk.get('prompt_eval_count'),
                                eval_count=chunk.get('eval_count'),
                                eval_duration=chunk.get('eval_duration')
                            )
            else:
                # Non-streaming response
                result = response.json()
                return OllamaResponse(
                    response=result.get('response', ''),
                    done=result.get('done', False),
                    context=result.get('context'),
                    total_duration=result.get('total_duration'),
                    load_duration=result.get('load_duration'),
                    prompt_eval_count=result.get('prompt_eval_count'),
                    eval_count=result.get('eval_count'),
                    eval_duration=result.get('eval_duration')
                )

        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to communicate with Ollama: {e}")
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Failed to parse Ollama response: {e}")

    def list_models(self) -> list:
        """
        List available models from Ollama.

        Returns:
            list: List of available model names

        Raises:
            requests.RequestException: If the HTTP request fails
        """
        url = f"{self.base_url}/api/tags"

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            return [model['name'] for model in result.get('models', [])]
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to list Ollama models: {e}")

    def check_connection(self) -> bool:
        """
        Check if Ollama service is reachable.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.list_models()
            return True
        except:
            return False

    def __repr__(self) -> str:
        """String representation of Ollama client."""
        return f"OllamaClient(base_url={self.base_url}, timeout={self.timeout})"