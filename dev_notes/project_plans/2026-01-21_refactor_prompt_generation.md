# Project Plan: Refactor Prompt Generation to BaseExecutor

**Objective**: Decentralize prompt generation logic from the `OnehotEngine` into the `BaseExecutor` and its subclasses. This allows each executor to define its own "Voice" and "Protocol" (e.g., Markdown for Cline vs. XML for Claude), resolving issues where Cline is confused by strict XML tags.

**Related Request**: `dev_notes/requests/prompt-17.md` (Implicit - current conversation)

## Context & Motivation
Currently, `OnehotEngine` and `PromptGenerator` enforce a single, strict prompt format (heavy XML, strict JSON requirements) for all agents.
- **Problem**: Cline (`cline_executor`) often fails because it gets confused by the XML tags or strict JSON instructions that conflict with its own internal system prompt and tool usage patterns.
- **Solution**: Move prompt generation responsibility to the `BaseExecutor`. This allows `ClineExecutor` to override the default strategy with a Markdown-based, tool-friendly format, while `ClaudeExecutor` keeps the robust XML format.

## Phase 1: Abstract Base Class Expansion
Expand `BaseExecutor` to include methods for constructing system instructions and full prompts.

- [ ] **Update `src/oneshot/providers/base.py`**:
    - Add `get_system_instructions(self, role: str) -> str`:
        - `role` can be `"worker"`, `"auditor"`, or `"reworker"`.
        - Returns the core behavioral instructions.
    - Add `format_prompt(self, task: str, role: str, header: Optional[str] = None, context: Optional[Dict] = None) -> str`:
        - Constructs the final prompt string.
        - `context` dict contains `iteration`, `auditor_feedback`, `worker_result`, etc.
    - Provide **default implementations** in `BaseExecutor` that mirror the current `PromptGenerator` logic (XML-based) to ensure backward compatibility for `ClaudeExecutor`, `AiderExecutor`, etc.

## Phase 2: Default Implementation (Legacy Logic)
Refactor the existing logic from `src/oneshot/protocol.py` (or `engine.py`) into the `BaseExecutor` default methods.

- [ ] **Migrate Logic**:
    - Move `WORKER_SYSTEM_PROMPT`, `AUDITOR_SYSTEM_PROMPT`, `REWORKER_SYSTEM_PROMPT` from `constants.py` (or `protocol.py`) to `BaseExecutor.get_system_instructions`.
    - Move XML construction logic from `PromptGenerator` to `BaseExecutor.format_prompt`.
- [ ] **Verify**: Ensure that `ClaudeExecutor` (which inherits defaults) produces identical prompts to the current system.

## Phase 3: Cline Override (The Fix)
Implement the specialized "Markdown Dialect" for `ClineExecutor`.

- [ ] **Update `src/oneshot/providers/cline_executor.py`**:
    - Override `get_system_instructions`:
        - Return instructions in **Markdown**.
        - Remove strict JSON/XML requirements.
        - Emphasize "Start your final response with '## Final Result'" or similar natural language markers.
    - Override `format_prompt`:
        - Construct a clean Markdown document:
          ```markdown
          # [Header]
          [System Instructions]

          ## Context
          Iteration: 2
          Feedback: ...

          ## Task
          [User Task]
          ```

## Phase 4: Engine Refactoring
Update the Engine to delegate prompt generation.

- [ ] **Update `src/oneshot/engine.py`**:
    - Remove `_generate_worker_prompt` and `_generate_auditor_prompt`.
    - Update `_execute_worker` to call `self.executor_worker.format_prompt(...)`.
    - Update `_execute_auditor` to call `self.executor_auditor.format_prompt(...)`.
    - Ensure all necessary context (iteration count, feedback, result summary) is passed in the `context` dictionary.

## Phase 5: Verification & Testing
- [ ] **Unit Tests**:
    - Create `tests/test_prompt_strategies.py`.
    - Verify `ClaudeExecutor` produces XML prompts.
    - Verify `ClineExecutor` produces Markdown prompts.
    - Verify context injection (iteration > 0) works for both.
- [ ] **Manual Verification**:
    - Run `oneshot "test task" --executor cline --debug` and verify the prompt structure in logs.
    - Run `oneshot "test task" --executor claude --debug` and verify the prompt structure in logs.

## Phase 6: Documentation Updates
- [ ] **Update `docs/project-structure.md`**: Reflect that prompt logic is now in Providers.
- [ ] **Update `docs/overview.md`**: Update architectural descriptions.
- [ ] **Update `AGENTS.md`**: If it references prompt locations.

## Deliverables
1. Refactored `BaseExecutor` with default XML strategy.
2. `ClineExecutor` with Markdown strategy.
3. Updated `OnehotEngine`.
4. Passing test suite.
