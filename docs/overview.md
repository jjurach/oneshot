# Oneshot Documentation Overview

This document provides a comprehensive index of all documentation in the oneshot project.

## Project Documentation

### Main Files
- **README.md** - Main project documentation, features, and quick start guide
- **CLAUDE.md** - Instructions for Claude AI integration (refers to AGENTS.md)
- **AGENTS.md** - Mandatory AI agent instructions for development tasks

## Documentation Structure

### `/docs/` Directory
Contains detailed technical documentation:

- **overview.md** (this file) - Documentation index and navigation guide
- **project-structure.md** - Locations of project components and architecture details
- **templates.md** - Mandatory templates for Project Plans and Change Documentation
- **streaming-and-state-management.md** - Design specification for streaming activity processing, state machine persistence, and resume/recovery features
- **cline-activity-json.md** - Documentation of Cline's JSON output format for activity streaming
- **direct-executor.md** - Direct executor implementation details for OpenAI-compatible endpoints
- **possible-todos.md** - Potential future improvements and tasks

## Quick Reference

### Command Line Usage
```bash
# Run oneshot with default settings
oneshot "Your task here"

# Use specific executor
oneshot --executor claude "Task"
oneshot --executor cline "Task"
oneshot --executor aider "Task"
oneshot --executor gemini "Task"

# Use direct provider (local models)
oneshot --worker-provider direct \
        --worker-endpoint http://localhost:11434/v1/chat/completions \
        --worker-model llama-pro \
        "Task"

# Configure logs directory
oneshot --logs-dir dev_notes/oneshot/ "Task"

# Resume previous session
oneshot --resume <oneshot-id> "Continue working"

# View status of running/completed execution
oneshot --view <oneshot-id>

# Follow activity log in real-time (tail -f style)
oneshot --follow <oneshot-id>

# Configure inactivity detection
oneshot --inactivity-threshold 300 "Task"  # 300 seconds
```

### Configuration
Session configuration can be controlled via:
- **Command-line arguments** - `oneshot --help` for full list
- **Session logs** - Located in configured logs directory (default: current directory)

## Supported Executors

Oneshot supports five executor types for autonomous task completion:

- **claude** - Claude CLI executor (requires Claude CLI installed and authenticated)
- **cline** - Cline VS Code extension integration (requires VS Code with Cline extension)
- **aider** - Aider code editor integration (requires Aider installation)
- **gemini** - Google Gemini CLI executor (requires Google Generative AI API access)
- **direct** - Direct API calls to OpenAI-compatible endpoints (local models via Ollama, OpenAI, Anthropic, Google, Groq, etc.)

### Executor Quick Reference

| Executor | Type | Installation | Best For |
|----------|------|--------------|----------|
| **claude** | CLI-based | `brew install anthropic/brew/claude` or `pip install claude-cli` | Integration with Claude models; high-quality responses |
| **cline** | VS Code Extension | Install Cline extension from VS Code Marketplace | VS Code workflows; file system operations |
| **aider** | CLI-based | `pip install aider-chat` | Code editing; working with source files |
| **gemini** | CLI-based | `pip install google-generativeai` or set API key | Google Gemini models; cost-effective solutions |
| **direct** | HTTP API | None (uses installed packages: `requests` or `httpx`) | Local models (Ollama), custom endpoints, multiple model options |

### Executor Selection Guide

- **For highest quality**: Use `claude` executor with Claude Opus or Sonnet models
- **For cost-effective local execution**: Use `direct` executor with Ollama
- **For VS Code integration**: Use `cline` executor
- **For code-specific tasks**: Use `aider` executor
- **For Google models**: Use `gemini` executor

## Architecture and Design

### Streaming Activity Processing

Oneshot is designed to provide real-time streaming updates from agent execution rather than batch dumps at completion. Key architectural components:

- **Activity Pipeline**: Standardized processing of agent outputs through parsing, logging, formatting, and display stages
- **NDJSON Activity Log**: Append-only `<oneshot-id>-oneshot-log.json` file containing timestamped activity packets
- **State Machine**: Persistent state tracking in `<oneshot-id>-oneshot.json` with full state transition history
- **Resume/Recovery**: Ability to resume interrupted executions and recover from failures

For complete details, see **streaming-and-state-management.md**.

### Prompt Generation System

Oneshot uses a decentralized prompt generation architecture where each executor defines its own prompt format and strategy:

- **BaseExecutor**: Provides default XML-based prompts for backward compatibility
- **ClineExecutor**: Uses Markdown-based prompts to avoid conflicts with Cline's internal prompt structure
- **Other Executors**: Inherit XML-based prompts from BaseExecutor

**Key Features:**
- Role-based instructions (worker, auditor, reworker)
- Context-aware formatting (iteration count, feedback, task results)
- Executor-specific dialects (XML vs Markdown)

For implementation details, see **project-structure.md**.

### Activity Log Format

Each executor's activity is captured in real-time as NDJSON (newline-delimited JSON):

```json
{"ts":1737395456789,"executor":"cline","oneshot_id":"abc-123","activity":{"type":"say","text":"..."}}
{"ts":1737395457123,"executor":"cline","oneshot_id":"abc-123","activity":{"type":"tool_use","tool":"read_file"}}
```

**Key Fields:**
- `ts`: Ingestion timestamp (milliseconds since epoch) - proves streaming behavior
- `executor`: Executor type (cline, claude, gemini, aider, direct)
- `oneshot_id`: Unique execution identifier
- `activity`: Original executor output JSON, preserved as-is

## Session Logging Format

Session state files use JSON format with the following structure:

```json
{
  "metadata": {
    "timestamp": "ISO 8601 datetime",
    "prompt": "original prompt text",
    "worker_provider": "executor|direct",
    "worker_model": "model name",
    "auditor_provider": "executor|direct",
    "auditor_model": "model name",
    "max_iterations": 5,
    "working_directory": "/path/to/working/dir",
    "status": "completed|in_progress",
    "completion_iteration": 3,
    "end_time": "ISO 8601 datetime"
  },
  "iterations": [
    {
      "iteration": 1,
      "worker_output": "...",
      "auditor_output": "..."
    }
  ]
}
```

## Demo Scripts and Examples

Oneshot includes example scripts demonstrating various features and executors:

Located in `examples/` directory:

- **demo_activity_formatter.py** - Demonstrates activity interpretation and formatting pipeline
- **demo_gemini_executor.py** - Showcases Google Gemini executor with different output formats and approval modes
- **demo_direct_executor.py** - Demonstrates direct executor functionality for local models via Ollama

See README.md for instructions on running demo scripts.

## Navigation Tips

- All dates in filenames use format: `YYYY-MM-DD_HH-MM-SS`
- Documentation is stored in git (except session logs which are .gitignored)
- Use `grep` or `find` to search across documentation
- Session logs can be reviewed to understand agent reasoning and tool usage
- Demo scripts in `examples/` directory provide practical usage examples for each executor
