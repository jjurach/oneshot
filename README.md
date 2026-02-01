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
- **Multiple Executors**: Supports `claude`, `cline`, `aider`, `gemini`, `codex`, and `direct` executors
- **Resume Capability**: Continue interrupted sessions from where they left off

## Supported Executors

Oneshot supports multiple executor types for autonomous task completion:

- **claude** - Claude CLI executor. See [Claude Code Guide](docs/system-prompts/tools/claude-code.md).
- **cline** - Cline VS Code extension integration. See [Cline Guide](docs/system-prompts/tools/cline.md).
- **aider** - Aider code editor integration. See [Aider Guide](docs/system-prompts/tools/aider.md).
- **gemini** - Google Gemini CLI executor. See [Gemini Guide](docs/system-prompts/tools/gemini.md).
- **codex** - Codex executor. See [Codex Guide](docs/system-prompts/tools/codex.md).
- **direct** - Direct API calls to OpenAI-compatible endpoints. See [Direct Executor Guide](docs/direct-executor.md).

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

# Use direct executor with Ollama
oneshot --executor direct "What is the capital of France?"

# Use direct executor with custom Ollama model
oneshot --executor direct --worker-model llama-pro:latest "Explain quantum computing"
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

## Configuration

Oneshot supports configuration files to set default values for command-line options. Create a configuration file at `~/.oneshot.json` to customize default settings.

### Configuration File

Create `~/.oneshot.json` with your preferred defaults:

```json
{
  "_comment": "Oneshot configuration file - place this at ~/.oneshot.json",
  "_note": "Command-line options override these defaults",
  "executor": "claude",
  "max_iterations": 5,
  "worker_model": "claude-3-5-sonnet-20241022",
  "auditor_model": "claude-3-5-haiku-20241022",
  "initial_timeout": 300,
  "max_timeout": 3600,
  "activity_interval": 30,
  "max_concurrent": 5,
  "idle_threshold": 60,
  "heartbeat_interval": 10,
  "web_port": 8000,
  "tui_refresh": 1.0
}
```

### Configuration Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `executor` | string | Executor to use: 'claude' or 'cline' | "cline" |
| `max_iterations` | integer | Maximum number of iterations | 5 |
| `worker_model` | string/null | Model for worker (null for executor defaults) | null |
| `auditor_model` | string/null | Model for auditor (null for executor defaults) | null |
| `initial_timeout` | integer | Initial timeout in seconds before activity monitoring | 300 |
| `max_timeout` | integer | Maximum timeout in seconds with activity monitoring | 3600 |
| `activity_interval` | integer | Activity check interval in seconds | 30 |
| `max_concurrent` | integer | Maximum concurrent tasks in async mode | 5 |
| `idle_threshold` | integer | Global idle threshold in seconds for async orchestrator | 60 |
| `heartbeat_interval` | integer | Heartbeat check interval in seconds for async orchestrator | 10 |
| `web_port` | integer | Port for web dashboard | 8000 |
| `tui_refresh` | float | TUI refresh rate in seconds | 1.0 |

### Precedence Rules

Configuration values are applied in this order (later values override earlier ones):

1. **Built-in defaults** (hardcoded in the code)
2. **Configuration file** (`~/.oneshot.json`)
3. **Command-line arguments** (highest precedence)

### Example Usage

Set Claude as your default executor:

```bash
echo '{"executor": "claude"}' > ~/.oneshot.json
oneshot "What is the capital of France?"
# Uses Claude executor by default, no need to specify --executor claude
```

Use different models for worker and auditor:

```bash
cat > ~/.oneshot.json << 'EOF'
{
  "executor": "claude",
  "worker_model": "claude-3-5-sonnet-20241022",
  "auditor_model": "claude-3-5-haiku-20241022"
}
EOF

oneshot "Complex task"
# Worker uses Sonnet, auditor uses Haiku
```

### Show Configuration

View the example configuration file:

```bash
oneshot --show-config
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
- `--show-config`: Show example configuration file content and exit

#### Provider Configuration Options

- `--worker-provider`: Worker provider type: 'executor' or 'direct'
- `--worker-endpoint`: API endpoint URL for worker when using direct provider
- `--worker-api-key`: API key for worker direct provider (optional for local models)
- `--auditor-provider`: Auditor provider type: 'executor' or 'direct'
- `--auditor-executor`: Executor to use for auditor when using executor provider
- `--auditor-endpoint`: API endpoint URL for auditor when using direct provider
- `--auditor-api-key`: API key for auditor direct provider (optional for local models)

## Documentation

### For AI Agents
- **[AGENTS.md](AGENTS.md)** - Mandatory workflow for AI agents
- **[Definition of Done](docs/definition-of-done.md)** - Quality standards
- **[Workflows](docs/workflows.md)** - Development workflows

### For Developers
- **[Documentation Index](docs/README.md)** - Complete documentation navigation
- **[Architecture](docs/architecture.md)** - System architecture
- **[Implementation Reference](docs/implementation-reference.md)** - Code patterns
- **[Contributing](docs/contributing.md)** - Contribution guidelines

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

## Demo Scripts and Examples

The `examples/` directory contains demo scripts showcasing various executor types and features:

### Activity Formatter Demo

Demonstrates the activity interpretation and formatting pipeline for processing NDJSON activity data:

```bash
python examples/demo_activity_formatter.py
```

**What it shows:**
- Reading and parsing NDJSON activity data
- Extracting meaningful activities from raw output
- Formatting activities for display
- Sensitive data filtering

### Gemini Executor Demo

Showcases Google Gemini executor functionality with different output formats and approval modes:

```bash
python examples/demo_gemini_executor.py
```

**Features demonstrated:**
- Gemini executor instantiation and configuration
- Output format options (json vs stream-json)
- Approval modes (normal vs auto-approve/yolo)
- Session logging capabilities

### Direct Executor Demo

Demonstrates direct executor functionality for querying local models via Ollama:

```bash
python examples/demo_direct_executor.py
```

**What it shows:**
- DirectExecutor instantiation
- Ollama client connection validation
- Simple query execution
- Model availability checking

### Running All Demos

Run all demo scripts in sequence:

```bash
for script in examples/demo_*.py; do
  echo "Running $script..."
  python "$script"
  echo "---"
done
```

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