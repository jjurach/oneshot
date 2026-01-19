# Change: Executor Session Dump Research and Documentation

**Date:** 2026-01-19
**Related Project Plan:** dev_notes/project_plans/2026-01-19_09-44-30_enhanced_session_logging_and_executor_support.md

## Overview

This document captures research findings on how to extract and dump session history from various executor tools (Claude CLI, Cline, Aider, and Gemini CLI). This information supports the implementation of comprehensive session logging in the oneshot framework.

## Claude CLI / Claude Code Session Dump Methods

### State File Locations
- Default path: `~/.claude/projects/` (stores JSONL files)
- Individual project chats stored as JSON objects

### CLI Commands and Tools
1. **Official Export (Web App/Desktop):** Settings > Privacy > Export Data
   - Returns email with downloadable data package
   - Not available from CLI directly

2. **Community Tool: claude-conversation-extractor**
   - GitHub: [ZeroSumQuant/claude-conversation-extractor](https://github.com/ZeroSumQuant/claude-conversation-extractor)
   - PyPI: [claude-conversation-extractor](https://pypi.org/project/claude-conversation-extractor/)
   - Commands:
     - `claude-start` - Interactive UI
     - `claude-extract --list` - List sessions
     - `claude-extract --extract 1,3,5` - Extract specific sessions
   - Supports: JSON, HTML export formats
   - Not officially affiliated with Anthropic

3. **Community Tool: claude-code-exporter**
   - GitHub: [claude-code-exporter](https://github.com/developerisnow/claude-code-exporter)
   - Installation: `npm install -g claude-code-exporter`
   - Commands:
     - `claude-prompts` - Export current projects
     - Supports JSON export and MCP server mode

4. **Alternative: Terminal Logging**
   - Use `script` command to capture all terminal output
   - Not structured, but captures complete session

### Implementation Strategy for Oneshot
- **Primary:** Use `claude-conversation-extractor` via subprocess calls
- **Fallback:** Manually read `~/.claude/projects/` JSONL files
- **Note:** Requires user to have community tool installed or requires direct file access

## Cline Session Dump Methods

### State File Locations
- Default path: `~/.cline/data/tasks/`
- Per-task storage:
  - `api_conversation_history.json` - Full conversation with API
  - `ui_messages.json` - UI message history
  - `task_metadata.json` - Task metadata

### CLI Commands
1. **Built-in Export:** History button in Cline UI
   - UI-based, not CLI accessible directly
   - Hover over chat → Export button
   - Exports to Markdown by default

2. **Task History Recovery:**
   - Command: "Cline: Reconstruct Task History" (VS Code command palette)
   - Scans task folders and rebuilds history index

3. **Batch Operations:**
   - Available in UI for cleanup and export
   - Favorites can be preserved during cleanup

### Implementation Strategy for Oneshot
- **Primary:** Read `api_conversation_history.json` files directly from `~/.cline/data/tasks/`
- **Parse:** JSON structure contains complete conversation history
- **Note:** Task ID needed to locate specific session
- **Fallback:** Export via subprocess if CLI command available

## Aider Session Dump Methods

### State File Locations
- Default chat history: `.aider.chat.history.md` (Markdown format)
- Configurable paths via:
  - `--chat-history-file` CLI option
  - Config file option: `chat-history-file`
  - Environment variables

### CLI Commands and Options
1. **No native export command** - Conversations automatically saved to Markdown
2. **Configuration options:**
   - `chat-history-file` (default: `.aider.chat.history.md`)
   - `llm-history-file` (separate LLM conversation log)
   - `restore-chat-history` (default: False) - Restore previous sessions

3. **File Access:**
   - Markdown logs automatically written during session
   - Can be copied/shared directly

### Implementation Strategy for Oneshot
- **Primary:** Read `.aider.chat.history.md` file directly as Markdown
- **Alternative:** Configure custom `--chat-history-file` path
- **Note:** File is automatically generated, no separate export command needed
- **Simple:** Just read the Markdown file after session completes

## Gemini CLI Session Dump Methods

### State File Locations
- Session storage: `~/.gemini/` (automatic, default)
- Temporary checkpoints: `~/.gemini/tmp/`
- Session browser accessible via `/resume` command

### CLI Commands
1. **Share Command:**
   - `/chat share file.md` - Export to Markdown
   - `/chat share file.json` - Export to JSON
   - Auto-generates filename if not specified

2. **Manual Checkpoints:**
   - `/chat save <tag>` - Save current conversation with tag
   - Saved to `~/.gemini/tmp/`

3. **Session Management:**
   - `/resume` - Open Session Browser (v0.20.0+)
   - Browse and search through previous sessions
   - Automatically saves all sessions (no manual action needed)

4. **Session Recovery:**
   - Auto-save enabled by default (v0.20.0+)
   - Can search and preview sessions before resuming

### Implementation Strategy for Oneshot
- **Primary:** Use `/chat share file.json` command via subprocess
- **Parse:** JSON format from exported file
- **Alternative:** Run Gemini CLI non-interactively with export command
- **Note:** Requires passing through interactive commands non-interactively

## Summary Table

| Tool | Format | Access Method | CLI Export | File-based | State Location |
|------|--------|----------------|-----------|-----------|----------------|
| Claude CLI | JSON/JSONL | Community tool | Via tool | Read files | `~/.claude/projects/` |
| Cline | JSON | Direct file read | No | `api_conversation_history.json` | `~/.cline/data/tasks/` |
| Aider | Markdown | Direct file read | No | `.aider.chat.history.md` | Project directory |
| Gemini CLI | JSON/Markdown | `/chat share` | Yes | Read saved exports | `~/.gemini/` |

## Recommendations for Oneshot Integration

1. **Cline (Easiest):** Directly read `api_conversation_history.json` from task folder
2. **Aider (Easy):** Directly read `.aider.chat.history.md` after session
3. **Gemini (Medium):** Use `/chat share` command or read auto-saved sessions
4. **Claude (Hard):** Requires community tool or direct JSONL file parsing

## Known Limitations

1. **Claude CLI:** No official CLI export; community tools may not be installed
2. **Cline:** Requires knowing task ID to locate correct session folder
3. **Aider:** Session history file location may vary with configuration
4. **Gemini:** Interactive `/chat share` command needs non-interactive wrapper

## Next Steps

- Implement file-based session dump reading for each executor
- Create executor-specific session extraction functions
- Add fallback strategies for each tool
- Document known limitations to users
- Test extraction with real executor sessions

## Sources

- [Claude Help Center: Export Data](https://support.claude.com/en/articles/9450526-how-can-i-export-my-claude-data)
- [claude-conversation-extractor on PyPI](https://pypi.org/project/claude-conversation-extractor/)
- [ZeroSumQuant/claude-conversation-extractor](https://github.com/ZeroSumQuant/claude-conversation-extractor)
- [Cline Task History Recovery Guide](https://docs.cline.bot/troubleshooting/task-history-recovery)
- [Aider In-chat Commands Documentation](https://aider.chat/docs/usage/commands.html)
- [Gemini CLI Session Management](https://geminicli.com/docs/cli/session-management/)
- [Google Developers Blog: Gemini CLI Session Management](https://developers.googleblog.com/pick-up-exactly-where-you-left-off-with-session-management-in-gemini-cli/)
