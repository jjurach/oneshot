# Project Plan: Customizable Worker & Auditor Prompts

## Objective

Make the worker and auditor prompt text customizable from command-line or configuration file, and add a short summary line at the beginning of each prompt (e.g., "oneshot execution in chatterbox project") to make the sessions created by `claude --resume` or `cline task list` more readable and identifiable.

## Implementation Steps

1. **Add Configuration Support**
   - Create a configuration system to read worker and auditor prompt prefixes/headers from:
     - Command-line arguments (`--worker-prompt-header`, `--auditor-prompt-header`)
     - Configuration file (e.g., `.oneshotrc` or `oneshot.config.yaml` in project root or home directory)
   - Define sensible defaults (e.g., "oneshot execution" for worker, "oneshot auditor" for auditor)
   - Implement precedence: CLI args > config file > defaults

2. **Modify Prompt Construction**
   - Update `WORKER_PREFIX` to accept a customizable header/summary line
   - Update `AUDITOR_PROMPT` to accept a customizable header/summary line
   - Format: "[header]\n\n[rest of prompt]" to create a short summary followed by blank line as requested
   - Ensure the header is informative but concise (one line max)

3. **Update Command-Line Arguments**
   - Add `--worker-prompt-header` argument (optional, defaults to "oneshot execution")
   - Add `--auditor-prompt-header` argument (optional, defaults to "oneshot auditor")
   - Add `--config` argument to specify custom config file location
   - Update help text and docstrings

4. **Implement Configuration File Reading**
   - Support `.oneshotrc` in current directory or home directory
   - Support `oneshot.config.yaml` or similar in current directory or home directory
   - Parse configuration to extract custom headers for worker and auditor
   - Gracefully handle missing/malformed config files

5. **Update Provider and Generator Code**
   - Ensure provider system passes the custom headers through to prompt generation
   - Update `call_executor` and related functions to use the customized prompts
   - Maintain backward compatibility with existing code

6. **Testing**
   - Write unit tests for configuration file parsing
   - Write unit tests for prompt construction with custom headers
   - Test CLI argument handling
   - Test precedence: CLI args > config file > defaults
   - Ensure backward compatibility (existing code works without configuration)

7. **Documentation**
   - Update README with configuration options
   - Add example `.oneshotrc` and `oneshot.config.yaml` files
   - Document command-line arguments in help text

## Success Criteria

- ✅ User can specify custom worker/auditor prompt headers via command-line
- ✅ User can specify custom prompt headers via configuration file
- ✅ Prompts display as "[header]\n\n[original prompt]" format
- ✅ Session names/IDs created by `claude --resume` reflect the custom headers
- ✅ Command `oneshot "task" --worker-prompt-header "oneshot in myproject"` works
- ✅ Configuration file in home directory or project root is automatically loaded
- ✅ Backward compatibility: existing code without custom headers still works
- ✅ All existing tests pass
- ✅ New functionality has test coverage

## Testing Strategy

1. **Unit Tests** (add to `tests/test_oneshot.py` and `tests/test_providers.py`)
   - Test prompt construction with custom headers
   - Test configuration file parsing (YAML, INI, or simple key=value)
   - Test CLI argument parsing for new flags
   - Test precedence logic (CLI > config file > defaults)
   - Test backward compatibility (no headers specified)

2. **Integration Tests**
   - Run end-to-end with custom headers
   - Verify session output format in logs
   - Verify `claude --resume` shows custom headers in session names

3. **Manual Testing**
   - Test `oneshot "task" --worker-prompt-header "custom"`
   - Test with `.oneshotrc` in current directory
   - Test with config file in home directory
   - Verify output format is correct

## Risk Assessment

- **Low Risk**: Configuration file parsing - use simple format (YAML or INI) with error handling
- **Low Risk**: CLI argument addition - straightforward argparse extension
- **Medium Risk**: Backward compatibility - ensure existing code paths still work without configuration
- **Low Risk**: Testing - comprehensive unit and integration tests will verify behavior

## Related Files to Modify

- `src/oneshot/oneshot.py` - Main file with WORKER_PREFIX and AUDITOR_PROMPT constants
- `src/oneshot/providers/__init__.py` - Provider system, configuration, and initialization
- `src/oneshot/main.py` (if exists) or update `main()` function in oneshot.py
- `tests/test_oneshot.py` - Add unit tests
- `tests/test_providers.py` - Add unit tests for configuration

## Related Configuration

- Create example `.oneshotrc` file
- Create example `oneshot.config.yaml` file
- Update README with usage examples
