"""
Configuration file handling for oneshot.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import sys

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# Default configuration values (matching CLI defaults)
DEFAULT_CONFIG = {
    "executor": "cline",
    "max_iterations": 1,  # Do not loop until we control context better
    "worker_model": None,  # Will be set based on executor
    "auditor_model": None,  # Will be set based on executor
    "worker_prompt_header": "oneshot execution",
    "auditor_prompt_header": "oneshot auditor",
    "initial_timeout": 300,
    "max_timeout": 3600,
    "activity_interval": 30,
    "max_concurrent": 5,
    "idle_threshold": 60,
    "heartbeat_interval": 10,
    "web_port": 8000,
    "tui_refresh": 1.0,
}


def get_config_paths() -> list[Path]:
    """
    Get all possible configuration file paths in order of precedence.

    Returns paths from most specific to least specific:
    1. Current directory: .oneshotrc, oneshot.config.yaml, .oneshot.json
    2. Home directory: .oneshotrc, oneshot.config.yaml, .oneshot.json
    """
    paths = []

    # Current directory (highest precedence)
    cwd = Path.cwd()
    paths.extend([
        cwd / '.oneshotrc',
        cwd / 'oneshot.config.yaml',
        cwd / '.oneshot.json',
    ])

    # Home directory
    home = os.environ.get('HOME')
    if not home:
        home = os.path.expanduser('~')
    home_path = Path(home)
    paths.extend([
        home_path / '.oneshotrc',
        home_path / 'oneshot.config.yaml',
        home_path / '.oneshot.json',
    ])

    return paths


def load_config_file(config_path: Path) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Load configuration from a specific file, auto-detecting format.

    Args:
        config_path: Path to config file

    Returns:
        Tuple of (config_dict, error_message)
    """
    if not config_path.exists():
        return {}, None

    try:
        # Detect format by file extension or content
        if config_path.suffix.lower() == '.yaml' or config_path.name.endswith('.config.yaml'):
            if not HAS_YAML:
                return {}, f"YAML support not available (install PyYAML to use {config_path.name})"
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f) or {}
        elif config_path.suffix.lower() == '.rc' or config_path.name == '.oneshotrc':
            # Simple INI-style format for .oneshotrc
            user_config = {}
            with open(config_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Try to parse as JSON for complex values, otherwise keep as string
                        try:
                            user_config[key] = json.loads(value)
                        except (json.JSONDecodeError, ValueError):
                            user_config[key] = value
                    else:
                        return {}, f"Invalid line {line_num} in {config_path.name}: expected key=value format"
        else:
            # Default to JSON
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)

        # Validate that user_config contains only known keys
        valid_keys = set(DEFAULT_CONFIG.keys())
        unknown_keys = set(user_config.keys()) - valid_keys

        if unknown_keys:
            return {}, f"Unknown configuration keys in {config_path.name}: {', '.join(sorted(unknown_keys))}. Valid keys: {', '.join(sorted(valid_keys))}"

        # Validate value types
        validation_error = _validate_config_types(user_config)
        if validation_error:
            return {}, f"Invalid configuration in {config_path.name}: {validation_error}"

        return user_config, None

    except json.JSONDecodeError as e:
        return {}, f"Invalid JSON in {config_path.name}: {e}"
    except yaml.YAMLError as e:
        return {}, f"Invalid YAML in {config_path.name}: {e}"
    except Exception as e:
        return {}, f"Error reading {config_path.name}: {e}"


def get_config_path() -> Path:
    """Get the path to the configuration file."""
    home = os.environ.get('HOME')
    if not home:
        # Fallback for systems without HOME
        home = os.path.expanduser('~')
    return Path(home) / '.oneshot.json'


def load_config(config_path: Optional[Path] = None) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Load configuration from file.

    Args:
        config_path: Path to config file, or None to use default location

    Returns:
        Tuple of (config_dict, error_message)
        If error_message is None, config was loaded successfully
    """
    if config_path is None:
        config_path = get_config_path()

    if not config_path.exists():
        # No config file found, return defaults
        return DEFAULT_CONFIG.copy(), None

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            user_config = json.load(f)

        # Validate that user_config contains only known keys
        valid_keys = set(DEFAULT_CONFIG.keys())
        unknown_keys = set(user_config.keys()) - valid_keys

        if unknown_keys:
            return DEFAULT_CONFIG.copy(), f"Unknown configuration keys: {', '.join(sorted(unknown_keys))}. Valid keys: {', '.join(sorted(valid_keys))}"

        # Merge user config with defaults
        config = DEFAULT_CONFIG.copy()
        config.update(user_config)

        # Validate value types
        validation_error = _validate_config_types(config)
        if validation_error:
            return DEFAULT_CONFIG.copy(), validation_error

        return config, None

    except json.JSONDecodeError as e:
        return DEFAULT_CONFIG.copy(), f"Invalid JSON in config file: {e}"
    except Exception as e:
        return DEFAULT_CONFIG.copy(), f"Error reading config file: {e}"


def _validate_config_types(config: Dict[str, Any]) -> Optional[str]:
    """Validate that config values have correct types."""
    # Type validation rules
    type_checks = {
        "executor": (str, lambda x: x in ["cline", "claude", "aider", "gemini"]),
        "max_iterations": (int, lambda x: x > 0),
        "worker_model": ((str, type(None)), lambda x: True),  # Can be string or None
        "auditor_model": ((str, type(None)), lambda x: True),  # Can be string or None
        "worker_prompt_header": (str, lambda x: len(x.strip()) > 0),  # Non-empty string
        "auditor_prompt_header": (str, lambda x: len(x.strip()) > 0),  # Non-empty string
        "initial_timeout": (int, lambda x: x > 0),
        "max_timeout": (int, lambda x: x > 0),
        "activity_interval": (int, lambda x: x > 0),
        "max_concurrent": (int, lambda x: x > 0),
        "idle_threshold": (int, lambda x: x > 0),
        "heartbeat_interval": (int, lambda x: x > 0),
        "web_port": (int, lambda x: 1 <= x <= 65535),  # Valid port range
        "tui_refresh": ((int, float), lambda x: x > 0),
    }

    for key, (expected_types, validator) in type_checks.items():
        value = config.get(key)
        if not isinstance(value, expected_types):
            return f"Invalid type for '{key}': expected {expected_types}, got {type(value)}"
        if not validator(value):
            return f"Invalid value for '{key}': {value}"

    return None


def apply_executor_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply executor-specific defaults for models.

    Args:
        config: Configuration dictionary

    Returns:
        Updated config with executor-specific defaults applied
    """
    config = config.copy()

    if config["executor"] == "claude":
        # Claude uses its own default model selection - don't force a model
        pass
    elif config["executor"] == "cline":
        # Cline doesn't support model selection
        if config["worker_model"] is not None:
            print(f"Warning: worker_model ignored for cline executor", file=sys.stderr)
        if config["auditor_model"] is not None:
            print(f"Warning: auditor_model ignored for cline executor", file=sys.stderr)
        config["worker_model"] = None
        config["auditor_model"] = None

    return config


def create_example_config() -> str:
    """Create an example configuration file content."""
    example_config = {
        "_comment": "Oneshot configuration file - place this at ~/.oneshot.json",
        "_note": "Command-line options override these defaults",
        "executor": "claude",
        "max_iterations": 5,
        "worker_model": "claude-3-5-sonnet-20241022",
        "auditor_model": "claude-3-5-haiku-20241022",
        "worker_prompt_header": "oneshot execution",
        "auditor_prompt_header": "oneshot auditor",
        "initial_timeout": 300,
        "max_timeout": 3600,
        "activity_interval": 30,
        "max_concurrent": 5,
        "idle_threshold": 60,
        "heartbeat_interval": 10,
        "web_port": 8000,
        "tui_refresh": 1.0
    }

    return json.dumps(example_config, indent=2, sort_keys=False)


# Global config cache
_config_cache = None
_config_error = None


def get_global_config() -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Get the global configuration, caching the result.

    Loads configuration from multiple file locations in order of precedence:
    1. Current directory files (.oneshotrc, oneshot.config.yaml, .oneshot.json)
    2. Home directory files (.oneshotrc, oneshot.config.yaml, .oneshot.json)
    """
    global _config_cache, _config_error

    if _config_cache is None:
        # Start with defaults
        config = DEFAULT_CONFIG.copy()
        errors = []

        # Try loading from each config file in order of precedence
        for config_path in get_config_paths():
            user_config, error = load_config_file(config_path)
            if error:
                errors.append(error)
                continue

            # Merge user config (later files override earlier ones)
            config.update(user_config)

        # Apply executor-specific defaults
        config = apply_executor_defaults(config)

        _config_cache = config

        # Combine any errors into a single error message
        if errors:
            _config_error = "; ".join(errors)
        else:
            _config_error = None

    return _config_cache, _config_error


def clear_config_cache():
    """Clear the configuration cache (useful for testing)."""
    global _config_cache, _config_error
    _config_cache = None
    _config_error = None
