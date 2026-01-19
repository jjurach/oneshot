# Project Plan: Enhanced Session Logging and Executor Support

**Date:** 2026-01-19 09:44:30
**Status:** Pending Approval
**Related Request:** dev_notes/requests/prompt-03.md

## Objective

Enhance the oneshot session logging system to provide more comprehensive information capture, rename session logs with a clear "oneshot" prefix, add support for the "gemini" executor, create documentation overview, implement configurable logs directory, and add demo scripts for the "direct" executor with Ollama integration.

## Implementation Steps

### 1. Rename Session Log Files to Use "oneshot" Prefix

**Files to modify:**
- `src/oneshot/oneshot.py` (line 669-670: session file naming)

**Changes:**
- Change session file naming from `session_{timestamp}.md` to `oneshot_{timestamp}.json`
- Update all references to session file patterns throughout the codebase
- Ensure backwards compatibility for reading existing session files

**Success Criteria:**
- New session logs created with format: `2026-01-19_09-44-30_oneshot.json`
- Old session files can still be resumed/read

### 2. Store Comprehensive Information in Session Logs

**Files to modify:**
- `src/oneshot/oneshot.py` (function `run_oneshot`, lines 633-780)

**New information to capture:**
- Original prompt text (already partially there, ensure it's in the log)
- Executor/provider configuration:
  - Executor type (claude, cline, aider, gemini, direct)
  - Worker model name
  - Auditor model name
  - Provider type (executor vs direct)
  - API endpoints (for direct provider)
- Working directory
- Session start/end timestamps
- Iteration timing information
- All agent reasoning and tool interactions from executors

**Approach:**
- Create a structured JSON session log format with sections:
  - `metadata`: Session configuration and environment info
  - `iterations`: Array of iteration objects containing worker/auditor exchanges
  - `agent_logs`: Embedded or referenced agent session logs from executors
- For Cline: Use `cline task list`, `cline task open $task_id`, `cline task view --output-format json` commands
- For Cline alternative: Read from `$HOME/.cline/data/tasks/$task_id/api_conversation_history.json`
- For Claude: Research via web search how to dump session history
- For Aider: Research via web search how to dump session history
- For Gemini: Research via web search how to dump session history
- Consider parallel markdown file (e.g., `2026-01-19_09-44-30_oneshot-data.md`) for human-readable format

**Success Criteria:**
- JSON log contains all required metadata fields
- Agent session logs are captured and stored (either embedded or referenced)
- Human-readable companion markdown file is generated
- No information loss from previous session log format

### 3. Research and Document Executor Session Dump Methods

**New file to create:**
- `dev_notes/changes/2026-01-19_09-44-30_executor_session_research.md`

**Research tasks:**
- Use WebSearch to find how to dump session history for:
  - Claude Code / Claude CLI
  - Aider
  - Gemini CLI
  - Cline (already partially known)
- Document findings with command examples
- Identify state file locations for each executor

**Success Criteria:**
- Documented methods for extracting session history from all supported executors
- Clear examples of CLI commands and file paths
- Fallback strategies when CLI methods are unavailable

### 4. Add Support for "gemini" Executor

**Files to modify:**
- `oneshot/providers/gemini_executor.py` (already exists, verify completeness)
- `oneshot/providers/__init__.py` (ensure gemini is exported)
- `src/oneshot/oneshot.py` (add gemini to valid executor choices)

**Changes:**
- Implement non-interactive mode for gemini-cli
- Add appropriate permission-bypass flags
- Ensure consistent interface with other executors
- Add configuration options for Gemini-specific parameters

**Success Criteria:**
- `oneshot --executor gemini "task"` works correctly
- Gemini executor supports all required provider methods
- Non-interactive execution works without user prompts
- Session logging captures Gemini-specific information

### 5. Update Documentation to List All Supported Executors

**Files to modify:**
- `README.md` (lines 7-9, 82-84, 139-148, etc.)
- All files in `docs/` directory

**Changes:**
- Add "gemini" to all executor lists
- Add "direct" to all executor lists where appropriate
- Ensure consistency across all documentation
- Add examples for each executor type

**Success Criteria:**
- All documentation mentions: claude, cline, aider, gemini, direct
- Examples provided for each executor type
- No outdated executor references remain

### 6. Create Demo Script for Direct Executor with Ollama

**New file to create:**
- `demo-direct-executor.sh` (or `demo-direct-executor.py`)

**Script requirements:**
- Use command-line arguments to invoke oneshot with direct executor
- Read model configuration from `.env` file
- Demonstrate with simple query: "What is the capital of Norway?"
- Show that direct executor with local Ollama model (llama-pro) works
- Include clear output and error handling

**Example command to demonstrate:**
```bash
#!/bin/bash
source .env
oneshot --worker-provider direct \
        --worker-endpoint http://localhost:11434/v1/chat/completions \
        --worker-model llama-pro \
        --auditor-provider direct \
        --auditor-endpoint http://localhost:11434/v1/chat/completions \
        --auditor-model llama-pro \
        "What is the capital of Norway?"
```

**Success Criteria:**
- Demo script runs without errors
- Successfully completes the test query
- Demonstrates direct executor integration with Ollama
- Clear output showing worker and auditor interactions

### 7. Evaluate Direct Executor LangChain/LangGraph Integration

**Tasks:**
- Check if LangChain/LangGraph integration exists in direct executor
- If present: Create checklist tasks to test the logic
- If absent: Create `docs/direct-executor.md` with detailed design

**For docs/direct-executor.md (if needed):**
- Architecture overview of direct executor
- Design for LangChain/LangGraph integration
- Context augmentation strategy
- Tooling extension framework
- Examples of extensible platform usage

**Success Criteria:**
- Clear determination of LangChain/LangGraph integration status
- If absent: Comprehensive design document created
- If present: Test checklist completed and validated

### 8. Create Documentation Overview

**New file to create:**
- `docs/overview.md`

**Content:**
- Index of all documentation in the project
- Brief description of each doc file
- Description of `dev_notes/` structure and accumulating documentation types:
  - `dev_notes/project_plans/` - AI-generated project implementation plans
  - `dev_notes/changes/` - AI-generated change documentation
  - `dev_notes/requests/` - User requests and feature prompts
  - `dev_notes/oneshot/` - Oneshot execution logs
- Links to all relevant documentation
- Quick start guides and references

**Success Criteria:**
- Complete index of all project documentation
- Clear descriptions of documentation organization
- Easy navigation for new developers/contributors

### 9. Implement Configurable Logs Directory

**Files to modify:**
- `src/oneshot/oneshot.py` (SESSION_DIR configuration, line 76)
- Configuration file support (if not present, add to config loading)
- Command-line argument parsing

**Changes:**
- Add `--logs-dir` command-line option
- Add `logs_dir` to configuration file schema (`~/.oneshot.json`)
- Update SESSION_DIR to use configured value
- Create logs directory if it doesn't exist
- Update default to support pattern like `dev_notes/oneshot/`

**Example configuration:**
```json
{
  "logs_dir": "dev_notes/oneshot"
}
```

**Success Criteria:**
- `--logs-dir` option works from command line
- `logs_dir` configuration in `~/.oneshot.json` is respected
- Logs directory is created automatically if missing
- Session logs are written to configured directory

### 10. Update .gitignore for Oneshot Logs

**Files to modify:**
- `.gitignore` (add oneshot log patterns)

**Changes:**
- Add pattern: `*oneshot*.json` (or more specific if needed)
- Add pattern: `*oneshot*.md` (for companion markdown files)
- Add pattern: `dev_notes/oneshot/` (if using that directory)
- Ensure massive log files don't get accidentally committed

**Success Criteria:**
- Git ignores oneshot session logs
- `.gitignore` patterns are specific enough to avoid false positives
- Existing important files are not ignored

### 11. Comprehensive Testing and Iteration

**Testing tasks:**
- Run `pytest` and ensure all tests pass
- Fix any test failures or warnings
- Run demo scripts (direct executor demo)
- Test each executor type (claude, cline, aider, gemini, direct)
- Verify session log generation and content
- Test configurable logs directory
- Check documentation completeness

**Iteration process:**
- If pytest fails: diagnose and fix, then re-run
- If demo scripts crash: diagnose and fix, then re-run
- Continue iterating until all tests and scripts work
- Review server logs for any crashes or errors

**Success Criteria:**
- All pytest tests pass without warnings
- All demo scripts run successfully
- No crashes in server logs
- Session logs contain all expected information
- All executors work correctly

### 12. Commit All Changes

**Commit requirements:**
- Stage all modified and new files
- Create descriptive commit message
- Include co-author attribution
- Ensure commit history is clean

**Files to commit:**
- Modified: `src/oneshot/oneshot.py`, `.gitignore`, `README.md`, docs files
- New: `demo-direct-executor.sh`, `docs/overview.md`, `docs/direct-executor.md` (conditional)
- New: Various change documentation in `dev_notes/changes/`
- Modified: Provider files for gemini executor

**Success Criteria:**
- All changes committed to git
- Clean commit message describing the enhancement
- No uncommitted changes remain
- Git history is coherent

## Testing Strategy

### Unit Tests
- Test session log JSON structure validation
- Test session file naming with new format
- Test logs directory configuration and creation
- Test backward compatibility with old session files
- Mock executor session dump extraction

### Integration Tests
- Test each executor type end-to-end:
  - Claude with session logging
  - Cline with session logging
  - Aider with session logging
  - Gemini with session logging
  - Direct with Ollama with session logging
- Test configurable logs directory with various paths
- Test session resume with new log format

### Demo/Smoke Tests
- Run demo-direct-executor script
- Verify output contains expected result
- Verify session log is created with complete metadata
- Verify logs are written to configured directory

### Regression Tests
- Ensure existing functionality still works
- Test old session files can still be read/resumed
- Verify backward compatibility

## Risk Assessment

### High Risk Areas
1. **Breaking Changes to Session Log Format:**
   - Risk: Existing tools/scripts that parse session logs may break
   - Mitigation: Maintain backward compatibility for reading old logs; provide migration guide

2. **Executor Session Dump Extraction:**
   - Risk: CLI commands or file paths may not work on all systems
   - Mitigation: Research thoroughly; provide fallback options; document known limitations

3. **Gemini Executor Integration:**
   - Risk: Gemini-cli may have different behavior or requirements
   - Mitigation: Thorough testing; clear error messages; document setup requirements

### Medium Risk Areas
1. **Configuration File Expansion:**
   - Risk: Configuration changes may confuse existing users
   - Mitigation: Maintain defaults; document new options clearly

2. **Logs Directory Configuration:**
   - Risk: Permissions issues or invalid paths could cause failures
   - Mitigation: Validate paths; create directories with appropriate error handling

### Low Risk Areas
1. **Documentation Updates:**
   - Risk: Documentation may become outdated
   - Mitigation: Review all docs for consistency; create overview index

2. **.gitignore Updates:**
   - Risk: May ignore unintended files
   - Mitigation: Use specific patterns; test with `git status`

## Dependencies

### External Dependencies
- Gemini CLI tool (for gemini executor)
- Cline CLI tool (for cline executor session dumps)
- Claude CLI tool (for claude executor session dumps)
- Aider CLI tool (for aider executor session dumps)
- Ollama (for direct executor demo)

### Internal Dependencies
- Provider system must be fully functional
- Configuration system must support new options
- Session management must handle both old and new formats

## Success Criteria

1. ✅ Session logs renamed with "oneshot" prefix
2. ✅ Session logs contain comprehensive metadata and agent interactions
3. ✅ Gemini executor fully integrated and functional
4. ✅ All documentation updated to include all executors
5. ✅ Demo script for direct executor works with Ollama
6. ✅ `docs/overview.md` created with complete documentation index
7. ✅ Configurable logs directory implemented
8. ✅ `.gitignore` updated to exclude oneshot logs
9. ✅ All pytest tests pass without warnings
10. ✅ All demo scripts run successfully
11. ✅ All changes committed to git
12. ✅ LangChain/LangGraph integration evaluated (tested or designed)

## Notes

- This is a large enhancement touching multiple areas of the codebase
- Prioritize backward compatibility to avoid breaking existing users
- Research phase for executor session dumps may reveal limitations
- Consider creating a session log format version number for future evolution
- The demo script serves as both documentation and smoke test
- LangChain/LangGraph evaluation may spawn a separate project plan
