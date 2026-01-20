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
- **possible-todos.md** - Potential future improvements and tasks

## Development Notes (`/dev_notes/`)

The `dev_notes/` directory contains AI-generated project documentation and tracks organized in several subdirectories:

### `dev_notes/project_plans/`
Contains detailed implementation plans created before development:
- `YYYY-MM-DD_HH-MM-SS_description.md` - Each plan describes objectives, implementation steps, testing strategy, and risk assessment
- Plans must be approved before implementation begins
- Example: `2026-01-19_09-44-30_enhanced_session_logging_and_executor_support.md`

### `dev_notes/changes/`
Contains change documentation created during implementation:
- `YYYY-MM-DD_HH-MM-SS_description.md` - Each entry documents what was modified
- Includes sections for related plan, overview, files modified, and impact assessment
- Example: `2026-01-18_00-18-33_provider-abstraction-implementation.md`

### `dev_notes/prompts/` (or `dev_notes/requests/`)
Contains user requests and feature prompts that trigger planning:
- Documents the original request and requirements
- Used as reference for creating project plans

### `dev_notes/oneshot/`
Contains session logs and execution records:
- Session logs are stored as `YYYY-MM-DD_HH-MM-SS_oneshot.json` files
- Includes complete metadata: prompt, provider config, timestamps, iterations
- Contains all worker and auditor outputs for each iteration
- Logs can be configured with `--logs-dir` option

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
oneshot --resume "Continue working"
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

## Session Logging Format

New session logs use JSON format with the following structure:

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

## Getting Started

1. **For Users**: See README.md for installation and basic usage
2. **For Developers**: See AGENTS.md for development workflow and project planning process
3. **For Understanding Changes**: Review dev_notes/changes/ for recent modifications
4. **For Session History**: Check dev_notes/oneshot/ for execution logs and results

## Development Workflow

1. **Request** → Create or reference a request in `dev_notes/requests/`
2. **Plan** → Create a project plan in `dev_notes/project_plans/`
3. **Approval** → Obtain explicit developer approval
4. **Implementation** → Execute the plan step-by-step
5. **Documentation** → Create change docs in `dev_notes/changes/`
6. **Commit** → Commit changes with descriptive messages
7. **Testing** → Run tests to verify all changes

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
