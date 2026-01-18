# Oneshot

Autonomous task completion with auditor validation.

Oneshot is a command-line tool that uses AI models in a worker-auditor loop to autonomously complete tasks. The worker attempts to complete the task, and an auditor validates the results, providing feedback for improvement until the task is successfully completed.

Currently supports Claude models (via `claude` command) and Cline (via `cline` command).

## Features

- **Autonomous Task Completion**: Uses AI models to complete tasks without constant human supervision
- **Auditor Validation**: Built-in validation loop ensures quality and correctness
- **Session Management**: Tracks progress across iterations with detailed session logs
- **Multiple Executors**: Supports both `claude` and `cline` executors
- **Configurable Models**: Choose different models for worker and auditor roles (Claude or xAI Grok)
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
- Access to Claude API (via `claude` command) or Cline (via `cline` command)
- The external executors must be properly configured and available in PATH

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