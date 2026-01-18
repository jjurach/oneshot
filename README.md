# Oneshot

Autonomous task completion with auditor validation.

Oneshot is a command-line tool that uses AI models in a worker-auditor loop to autonomously complete tasks. The worker attempts to complete the task, and an auditor validates the results, providing feedback for improvement until the task is successfully completed.

Supports multiple provider types:
- **Executor providers**: Claude (via `claude` command) and Cline (via `cline` command)
- **Direct providers**: OpenAI-compatible API endpoints (Ollama, OpenAI, etc.)

## Features

- **Autonomous Task Completion**: Uses AI models to complete tasks without constant human supervision
- **Auditor Validation**: Built-in validation loop ensures quality and correctness
- **Session Management**: Tracks progress across iterations with detailed session logs
- **Flexible Provider System**:
  - **Executor Provider**: Subprocess-based executors (`claude`, `cline`)
  - **Direct Provider**: Direct HTTP API calls to OpenAI-compatible endpoints
  - **Mixed Providers**: Use different providers for worker and auditor (e.g., expensive commercial worker + free local auditor)
- **Local Model Support**: Direct integration with Ollama and other OpenAI-compatible APIs
- **Multiple Executors**: Supports both `claude` and `cline` executors
- **Configurable Models**: Choose different models for worker and auditor roles
- **Resume Capability**: Continue interrupted sessions from where they left off

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/oneshot.git
cd oneshot

# Install in development mode
pip install -e .

# Or install with development dependencies
pip install -e .[dev]
```

### From PyPI (once published)

```bash
pip install oneshot
```

## Usage

### Basic Usage

```bash
oneshot "What is the capital of France?"
```

### Advanced Options

```bash
# Use specific models
oneshot --worker-model claude-3-5-sonnet-20241022 --auditor-model claude-3-5-haiku-20241022 "Complex task"

# Set maximum iterations
oneshot --max-iterations 10 "Difficult task"

# Configure timeouts for long-running tasks
oneshot --initial-timeout 600 --max-timeout 7200 --activity-interval 60 "Long running task"

# Resume a previous session
oneshot --resume 'Continue working on this'

# Use specific session file
oneshot --session session_20230101_120000.md --resume "Continue from specific session"

# Specify custom session log file
oneshot --session-log my_task_log.md "Task with custom logging"

# Keep session log after completion
oneshot --keep-log "Task where I want to keep the log"

# Enable verbose output
oneshot --verbose "Debug this task"

# Use cline executor instead of claude
oneshot --executor cline "Task for cline"
```

### Provider Configuration

Oneshot supports flexible provider configuration, allowing you to mix and match different providers for worker and auditor roles:

#### Provider Types

- **executor**: Subprocess-based executors (claude, cline)
- **direct**: Direct HTTP API calls to OpenAI-compatible endpoints

#### Using Local Models (Direct Provider)

Run both worker and auditor with local Ollama:

```bash
oneshot --worker-provider direct \
        --worker-endpoint http://localhost:11434/v1/chat/completions \
        --worker-model qwen3-8b-coding \
        --auditor-provider direct \
        --auditor-endpoint http://localhost:11434/v1/chat/completions \
        --auditor-model qwen3-8b-coding \
        "What is 2+2?"
```

#### Mixed Providers

Use expensive model for worker, cheap local model for auditor:

```bash
oneshot --worker-provider executor \
        --executor claude \
        --worker-model claude-opus-4-5-20251101 \
        --auditor-provider direct \
        --auditor-endpoint http://localhost:11434/v1/chat/completions \
        --auditor-model qwen3-8b-coding \
        "Write a complex Python function"
```

#### Using OpenAI API

```bash
oneshot --worker-provider direct \
        --worker-endpoint https://api.openai.com/v1/chat/completions \
        --worker-model gpt-4 \
        --worker-api-key $OPENAI_API_KEY \
        --auditor-provider direct \
        --auditor-endpoint https://api.openai.com/v1/chat/completions \
        --auditor-model gpt-3.5-turbo \
        --auditor-api-key $OPENAI_API_KEY \
        "Complete this task"
```

#### Different Executors

Use different executors for worker and auditor:

```bash
oneshot --worker-provider executor \
        --executor claude \
        --worker-model claude-3-5-sonnet-20241022 \
        --auditor-provider executor \
        --auditor-executor cline \
        "Task description"
```

### Command Line Options

- `prompt`: The task to complete (required)
- `--max-iterations`: Maximum number of iterations (default: 5)
- `--worker-model`: Model for the worker (default: claude-3-5-haiku-20241022)
- `--auditor-model`: Model for the auditor (default: claude-3-5-haiku-20241022)
- `--initial-timeout`: Initial timeout in seconds before activity monitoring (default: 300)
- `--max-timeout`: Maximum timeout in seconds with activity monitoring (default: 3600)
- `--activity-interval`: Activity check interval in seconds (default: 30)
- `--resume`: Resume the most recent session
- `--session`: Specific session file to resume
- `--session-log`: Path to session log file (will append if exists, will not auto-delete)
- `--keep-log`: Keep the session log file after completion
- `--verbose`: Enable verbose output with buffer dumps
- `--debug`: Enable debug output with detailed internals
- `--executor`: Executor to use: 'claude' or 'cline' (default: cline)

#### Provider Configuration Options

- `--worker-provider`: Worker provider type: 'executor' or 'direct'
- `--worker-endpoint`: API endpoint URL for worker when using direct provider
- `--worker-api-key`: API key for worker direct provider (optional for local models)
- `--auditor-provider`: Auditor provider type: 'executor' or 'direct'
- `--auditor-executor`: Executor to use for auditor when using executor provider
- `--auditor-endpoint`: API endpoint URL for auditor when using direct provider
- `--auditor-api-key`: API key for auditor direct provider (optional for local models)

## How It Works

Oneshot operates in a worker-auditor loop:

1. **Worker Phase**: The worker model attempts to complete the given task, providing a JSON response with status, result, confidence, validation, and execution proof.

2. **Auditor Phase**: The auditor model evaluates the worker's response and decides whether the task is complete or needs reiteration.

3. **Iteration**: If the auditor requests changes, the process repeats with feedback incorporated into the next worker prompt.

4. **Completion**: The loop continues until the auditor confirms completion or the maximum iterations are reached.

## Session Logs

All interactions are logged to timestamped markdown files in the current directory:
- Format: `session_YYYYMMDD_HHMMSS.md`
- Contains: Full worker outputs, auditor responses, and session metadata
- Useful for reviewing completed work and debugging issues

## Requirements

- Python 3.8+
- For executor provider:
  - Access to Claude API (via `claude` command) or Cline (via `cline` command)
  - The external executors must be properly configured and available in PATH
- For direct provider:
  - `requests` library (for synchronous HTTP calls)
  - `httpx` library (for asynchronous HTTP calls)
  - Access to an OpenAI-compatible API endpoint (e.g., Ollama, OpenAI, etc.)

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e .[dev]

# Run tests
pytest

# Run with coverage
pytest --cov=oneshot --cov-report=html
```

### Building for Distribution

```bash
# Build distribution packages
python -m build

# Upload to PyPI (requires API token)
twine upload dist/*
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.