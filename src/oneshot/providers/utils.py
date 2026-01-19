import os
import subprocess
from typing import Dict, Optional

def run_command(
    command: str,
    env: Optional[Dict[str, str]] = None,
    capture_output: bool = True,
    check: bool = False
) -> subprocess.CompletedProcess:
    """
    Utility function for running shell commands with enhanced configuration.

    Args:
        command (str): The command to execute
        env (Dict[str, str], optional): Environment variables to use
        capture_output (bool, default True): Capture command output
        check (bool, default False): Raise exception on non-zero return code

    Returns:
        subprocess.CompletedProcess: Result of command execution
    """
    # If no env provided, use current environment
    effective_env = env or os.environ.copy()

    try:
        return subprocess.run(
            command,
            shell=True,
            env=effective_env,
            capture_output=capture_output,
            text=True,
            check=check
        )
    except subprocess.CalledProcessError as e:
        # Log or handle the error as needed
        return e

def map_api_keys(base_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Map and secure API keys from environment variables.

    Args:
        base_env (Dict[str, str], optional): Base environment to map keys from

    Returns:
        Dict[str, str]: Mapped and sanitized API keys
    """
    # Start with base environment or current environment
    env = base_env or os.environ.copy()

    # Key mappings and sanitization
    api_key_map = {
        'OPENAI_API_KEY': 'PROVIDER_PRIMARY_KEY',
        'ANTHROPIC_API_KEY': 'PROVIDER_SECONDARY_KEY',
        'GOOGLE_API_KEY': 'PROVIDER_TERTIARY_KEY'
    }

    # Create a new environment with mapped keys
    return {
        mapped_key: env.get(original_key, '')
        for original_key, mapped_key in api_key_map.items()
    }