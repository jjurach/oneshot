# Project Workflows

This document describes development workflows specific to oneshot.

## Core Agent Workflow

All AI agents working on this project must follow the **A-E workflow** defined in [AGENTS.md](../AGENTS.md):

- **A: Analyze** - Understand the request and declare intent
- **B: Build** - Create project plan
- **C: Code** - Implement the plan
- **D: Document** - Update documentation
- **E: Evaluate** - Verify against Definition of Done

For complete workflow documentation, see the [Agent Kernel Workflows](system-prompts/workflows/).

## Project-Specific Workflows

### Testing Workflow

Always run tests before proposing or committing changes.

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_executor_framework.py
```

### Development Workflow

1. Identify the component to modify (e.g., a specific executor).
2. Create a Project Plan in `dev_notes/project_plans/`.
3. Obtain human approval.
4. Implement changes in `src/`.
5. Add/update tests in `tests/`.
6. Document changes in `dev_notes/changes/`.
7. Verify against `docs/definition-of-done.md`.

## See Also

- [AGENTS.md](../AGENTS.md) - Core A-E workflow
- [Definition of Done](definition-of-done.md) - Quality checklist
- [Architecture](architecture.md) - System design
- [Implementation Reference](implementation-reference.md) - Code patterns
- [Agent Kernel Workflows](system-prompts/workflows/) - Complete workflow documentation

---
Last Updated: 2026-02-01