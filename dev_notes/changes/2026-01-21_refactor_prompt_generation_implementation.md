# Change Documentation: Refactor Prompt Generation Implementation

**Date:** 2026-01-21
**Time:** 12:06:34 PM (America/Chicago, UTC-6:00)
**Related Plan:** `dev_notes/project_plans/2026-01-21_refactor_prompt_generation.md`

## Overview

Successfully implemented the prompt generation refactor to decentralize prompt logic from the OnehotEngine into individual executor classes. This allows each executor to define its own "Voice" and "Protocol" (e.g., Markdown for Cline vs. XML for Claude), resolving issues where Cline gets confused by strict XML tags.

## Files Modified

### Core Implementation
- **`src/oneshot/providers/base.py`**
  - Added abstract methods: `get_system_instructions(role: str)` and `format_prompt(task: str, role: str, header: str, context: dict)`
  - Implemented default XML-based prompt generation for backward compatibility
  - Migrated existing logic from `constants.py` and `engine.py`

- **`src/oneshot/providers/cline_executor.py`**
  - Added Markdown-based prompt generation override
  - Implemented clean Markdown structure with headers and sections
  - Added Cline-specific system instructions without XML tags

- **`src/oneshot/engine.py`**
  - Refactored `_generate_worker_prompt()` to delegate to executor
  - Refactored `_generate_auditor_prompt()` to delegate to executor
  - Removed hardcoded prompt generation logic

### Testing
- **`tests/test_prompt_strategies.py`** (new file)
  - Comprehensive test suite for prompt generation strategies
  - Tests both XML (BaseExecutor) and Markdown (ClineExecutor) formats
  - Integration tests ensuring different executors produce different prompts
  - Backward compatibility verification

### Documentation
- **`docs/project-structure.md`**
  - Added "Prompt Generation" section explaining executor-specific strategies
  - Updated executor descriptions to mention prompt formats (XML vs Markdown)
  - Documented key methods: `get_system_instructions()` and `format_prompt()`

- **`docs/overview.md`**
  - Added "Prompt Generation System" section in Architecture and Design
  - Explained decentralized architecture and executor-specific dialects

## Technical Details

### New Architecture
- **BaseExecutor**: Provides XML-based prompts as default implementation
- **ClineExecutor**: Overrides with Markdown-based prompts to avoid Cline conflicts
- **Other Executors**: Inherit XML prompts from BaseExecutor (backward compatible)

### Key Methods Added
```python
def get_system_instructions(self, role: str) -> str:
    """Returns role-specific system instructions (worker/auditor/reworker)"""

def format_prompt(self, task: str, role: str, header: str, context: dict) -> str:
    """Formats complete prompt with task, context, and instructions"""
```

### Prompt Formats
- **XML Format** (BaseExecutor): Uses `<instruction>` tags, strict JSON requirements
- **Markdown Format** (ClineExecutor): Uses `# Headers`, `## Sections`, natural language guidance

## Impact Assessment

### Benefits
- ✅ **Solves Cline Issues**: Cline no longer gets confused by XML tags conflicting with its internal prompts
- ✅ **Backward Compatible**: Existing Claude/Gemini/Aider executors continue working unchanged
- ✅ **Extensible**: New executors can easily define their own prompt strategies
- ✅ **Decentralized**: Prompt logic lives with the executor that understands its requirements

### Risks Addressed
- ✅ **No Breaking Changes**: All existing functionality preserved
- ✅ **Test Coverage**: Comprehensive test suite ensures correctness
- ✅ **Documentation**: Clear docs for future maintainers

### Performance Impact
- **Neutral**: No performance impact - prompt generation moved from engine to executor (same total work)
- **Memory**: No significant memory changes

## Testing Results

- **Unit Tests**: 16/16 tests pass in `test_prompt_strategies.py`
- **Integration Tests**: All existing tests continue to pass (350 passed, 2 skipped)
- **Manual Verification**: Confirmed different executors produce appropriately formatted prompts

## Verification Steps

1. **XML Prompts**: BaseExecutor produces XML-structured prompts with `<instruction>` tags
2. **Markdown Prompts**: ClineExecutor produces clean Markdown with headers and sections
3. **Context Injection**: Both formats properly inject iteration counts, feedback, and task results
4. **Backward Compatibility**: Existing executors inherit XML prompts without changes

## Next Steps

- Monitor Cline executor performance with new Markdown prompts
- Consider implementing custom prompt strategies for other executors if needed
- Update any executor-specific documentation that references old prompt locations

## Commit Information

This change implements the approved project plan `2026-01-21_refactor_prompt_generation.md` and resolves the issue where Cline executor was confused by XML prompt structures.