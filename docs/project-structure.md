# Project Structure & Component Reference

This document outlines the location of key project components and implementations.

## Directory Overview

- **`src/oneshot/`**: Main application source code.
- **`src/oneshot/providers/`**: Executor implementations and activity processing logic.
- **`docs/`**: Detailed documentation (architecture, conventions, templates).
- **`dev_notes/`**: AI-generated Project Plans and Change Documentation.
- **`tests/`**: Pytest test suite.
- **`examples/`**: Demo scripts and examples.

## Executors

**Location:** `src/oneshot/providers/`

| Executor | File | Description |
|----------|------|-------------|
| **Base** | `base.py` | Base abstract executor class. |
| **Cline** | `cline_executor.py` | Integration with Cline VS Code extension. |
| **Claude** | `claude_executor.py` | Integration with Anthropic's Claude CLI. |
| **Gemini** | `gemini_executor.py` | Integration with Google Gemini CLI. |
| **Aider** | `aider_executor.py` | Integration with Aider CLI. |
| **Direct** | `direct_executor.py` | Direct API execution (OpenAI-compatible). |

## Core Logic

**Location:** `src/oneshot/`

- **Activity Processing**:
  - `providers/activity_formatter.py`
  - `providers/activity_interpreter.py`
  - `providers/activity_logger.py`

## Testing & Demos

- **Tests**: `tests/`
  - `test_executor_framework.py`: Core executor tests.
  - `test_*_executor.py`: Specific executor tests.
- **Demos**: `examples/`
  - `demo_direct_executor.py`
  - `demo_gemini_executor.py`
  - `demo_activity_formatter.py`
