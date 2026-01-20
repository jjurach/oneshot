# MANDATORY AI Agent Instructions (Condensed)

**CRITICAL:** This document contains the essential, non-negotiable rules for all development tasks. You are responsible for knowing and following every rule here. Detailed explanations, full templates, and non-critical best practices are located in the `/docs` directory.

---

## 1. The Core Workflow

**MANDATORY:** For any request that involves creating or modifying code or infrastructure, you MUST follow this workflow.

**Step A: Analyze the Request & Declare Intent**
1.  **Is it a simple question?** → Answer it directly.
2.  **Is it a Trivial Change?** → Make the change directly. No documentation required.
3.  **Is it anything else?** → Announce you will create a **Project Plan**.

> **Trivial Change Definition:** Non-functional changes like fixing typos in comments or code formatting. The full definition and examples are in `docs/01_overview.md`.

**Step B: Create a Project Plan (If Required)**
- Use the `Project Plan` structure defined in Section 3.
- The plan must be detailed enough for another agent to execute.
- Save the plan to `dev_notes/project_plans/YYYY-MM-DD_HH-MM-SS_description.md`.

**Step C: AWAIT DEVELOPER APPROVAL**
- **NEVER EXECUTE A PLAN WITHOUT EXPLICIT APPROVAL.**
- Present the full Project Plan to the developer.
- "Approved", "proceed", "go ahead", "ok", or "yes" mean you can start.
- If the developer asks questions or provides feedback, answer them and then **return to a waiting state** until you receive a new, explicit approval.
- **If approval is ambiguous** (e.g., "maybe", "I think so", "probably"): Ask a follow-up clarifying question such as "I want to confirm: should I proceed with this Project Plan? Please respond with 'yes' or 'no'."

**Step D: Implement & Document Concurrently**
- Execute the approved plan step-by-step.
- After each logical change, create or update a **Change Documentation** entry in `dev_notes/changes/`. Use the structure from Section 3.

---

## 2. Project Component & Skill Routing Guide

General references to "planning" e.g. "plan this" or "Start thinking about next project plan" should be interpreted to trigger focus on a project plan, either already created and unimplemented or implemented.
- sometimes the initial prompt should infer creating a checklist of items which includes:
  - adding and re-iterating on unit tests for any new code
  - ensuring the global `pytest` unit test works
  - committing your work
- in other words, a "simple" request may generate a large plan with "boilerplate" a simple agent can execute to complete the "simple" request.
- generally, if the request is about planning, and does not mention "implement" or "execute", then stop and consider the completed project plan a success.
  - if the complex task (e.g. "add --verbose flag") does not mention "planning", then both create the plan and start executing the plan.
- The plan and changes will be committed with the other contributions of the task.

**MANDATORY:** Use this guide to locate project components.

- **`infrastructure/`**: Terraform for AWS ECS deployment.
- **`api/openapi.yaml`**: **The API's single source of truth.** Changes here are critical and must be planned carefully as they impact all frontends and the backend.
- **`docs/`**: Detailed documentation (architecture, conventions, full templates).
- **`dev_notes/`**: All AI-generated Project Plans and Change Documentation.

---

## 2.1. Documentation Index & Quick Reference

### Active Project Plans

#### Documentation Cleanup & Validation for Executor Abstraction
**Source**: `dev_notes/requests/prompt-12.md`
**Detailed Plan**: `dev_notes/project_plans/2026-01-20_10-15-00_documentation-cleanup.md`

- **Objective**: Perform comprehensive documentation review and cleanup following executor abstraction implementation, ensuring all five executors (cline, claude, aider, gemini, direct) are consistently represented and documented
- **Key Deliverables**:
  - Audit of all documentation references to each executor
  - Verification that executor lists are complete across all docs
  - Cleanup of redundant/superfluous documentation
  - Testing and fixes for all demo scripts
  - Updated README.md with complete demo script instructions
- **Implementation Phases**:
  1. Documentation audit & cleanup for each executor (cline, claude, aider, gemini, direct)
  2. Documentation consolidation and removal of redundancies
  3. Demo script validation and bug fixes
  4. README.md updates with demo script instructions
  5. Final validation and verification
- **Status**: Plan created, awaiting approval
- **Complexity**: Medium (systematic review and validation task)

#### Executor Abstraction Refactor
**Source**: `dev_notes/requests/prompt-11.md`
**Detailed Plan**: `dev_notes/project_plans/2026-01-20_08-27-00_executor-abstraction-refactor.md`

- **Objective**: Consolidate all agent execution logic (cline, claude, gemini, aider, direct) into a unified, extensible executor architecture
- **Key Deliverables**:
  - Base `Executor` abstract class with standardized interface (in `src/oneshot/providers/base.py`)
  - Five executor implementations: `ClineExecutor`, `ClaudeExecutor`, `GeminiExecutor`, `AiderExecutor`, `DirectExecutor`
    - Each isolated to its own file: `src/oneshot/providers/{executor_name}_executor.py`
    - Each implements: `select_command()`, `parse_activity()`, `format_output()`, `executor_type` property
    - All executor-specific references isolated within executor classes
  - Comprehensive test suite (`tests/test_executor_framework.py`) covering:
    - Command construction for all executors
    - Activity parsing (streaming format interpretation) for all executors
    - Output formatting for all executors
    - Edge cases and error conditions
  - Demo scripts with live checklist tracking:
    - `demo_executor_single.py`: Single executor demonstration with progress checklist
    - `demo_executor_all.py`: Cross-executor comparison with progress tracking
  - Developer guide (`docs/executor_implementation_guide.md`) for implementing new executors
- **Status**: Plan approved, awaiting implementation
- **Complexity**: High (6 phases, affects core architecture)
- **Key Methods** (standardized interface):
  - `select_command()`: Choose and construct executor-specific command
  - `parse_activity()`: Parse streaming activity into structured results (stdout summary + audit details)
  - `format_output()`: Generate formatted output for display and audit log
  - `executor_type` (property): Identifier string for executor (e.g., "cline", "claude", "gemini", "aider", "direct")
- **Implementation Phases**:
  1. Base executor architecture design with abstract interface
  2. Implement five executor classes, isolating all executor-specific logic
  3. Create comprehensive test suite with cross-executor validation
  4. Create demo scripts with detailed checklist tracking for each step
  5. Documentation (guide + AGENTS.md updates)
  6. Final validation, regression testing, and commit
- **Testing Requirements**:
  - Unit tests for each executor (command, activity parsing, output formatting)
  - All executor tests passing (no failures)
  - Full pytest suite passes (no regressions in existing code)
  - Demo scripts execute without errors
  - Activity parsing validated across all executor formats
- **Progress Tracking**:
  - Use detailed checklists in each Phase (update upon completion)
  - Demo scripts include live checklist updates during execution
  - Run full test suite after each major phase

### Project Components Reference
- **Executors Location**: `src/oneshot/providers/`
- **Existing Implementations**:
  - `base.py` - Base executor class (may need refactoring)
  - `cline_executor.py` - Cline integration
  - `claude_executor.py` - Claude Code integration
  - `gemini_executor.py` - Gemini execution
  - `aider_executor.py` - Aider execution
  - `direct_executor.py` - Direct OpenAI execution
- **Activity Processing**: `activity_formatter.py`, `activity_interpreter.py`, `activity_logger.py`
- **Tests Location**: `tests/`
- **Demo Scripts**: Root directory (`demo_*.py`)

---

## 3. Documentation Structures (Checklists)

**MANDATORY:** All Project Plans and Change Documentation you create must include these sections. Full, detailed templates are in `docs/templates.md`.

### Project Plan Structure
- `# Project Plan: [Project Name]`
- `Objective`
- `Implementation Steps` (Detailed list of actions)
- `Success Criteria`
- `Testing Strategy`
- `Risk Assessment`

### Change Documentation Structure
- `# Change: [Brief Description]`
- `Related Project Plan`
- `Overview` of the change.
- `Files Modified` with a summary of what changed in each.
- `Impact Assessment`

---

## 4. The Unbreakable Rules

1.  **Approval is Mandatory:** This is the most important rule. Never act on a Project Plan without explicit developer approval.
2.  **Quality is Mandatory:** You MUST follow the existing code patterns, conventions, style, and typing of the files you are editing. New code should look like the old code.
3.  **Uncertainty Requires a Full Stop:** If you encounter any error, are confused by a requirement, or are unsure how to proceed, you MUST **STOP** immediately. Document the issue and ask the developer for guidance. Do not try to solve novel problems alone.
4.  **File Naming is Mandatory:** All Project Plans and Change Documentation in `dev_notes/` MUST use the `YYYY-MM-DD_HH-MM-SS_description.md` format.
5.  **Temporary Files:** NEVER use `/tmp` or system temporary directories for temporary files. Always create temporary files in the current working directory using the naming patterns `tmp-*` or `*.tmp` or `tmp/*`. These files should be cleaned up when no longer needed.
6.  **Slack Notification (If Supported):** Notify using the slack-notifications MCP service each time you commit to the local git repo. See `docs/06_tools_and_integrations.md` for setup instructions. **Note:** This rule applies only to agents with MCP support (e.g., Claude Code). Agents without MCP capabilities may skip this step.

This condensed file preserves all mandatory instructions while significantly reducing the token count, making it suitable for models with smaller context windows.
