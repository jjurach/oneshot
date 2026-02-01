# Definition of Done - oneshot

**Referenced from:** [AGENTS.md](../AGENTS.md)

This document defines the "Done" criteria for oneshot. It extends the universal Agent Kernel Definition of Done with project-specific requirements.

## Agent Kernel Definition of Done

This project follows the Agent Kernel Definition of Done. **You MUST review these documents first:**

### Universal Requirements

See **[Universal Definition of Done](system-prompts/principles/definition-of-done.md)** for:
- Plan vs Reality Protocol
- Verification as Data
- Codebase State Integrity
- Agent Handoff
- Status tracking in project plans
- dev_notes/ change documentation requirements

### Python Requirements

See **[Python Definition of Done](system-prompts/languages/python/definition-of-done.md)** for:
- Python environment & dependencies
- Testing requirements (pytest)
- Code quality standards
- File organization
- Coverage requirements

## Project-Specific Extensions

The following requirements are specific to oneshot and extend the Agent Kernel DoD:

### 1. Executor Safety

**Mandatory Checks:**
- [ ] Any new executor must handle subprocess termination cleanly.
- [ ] Shell commands must be escaped or validated if they contain user input.

### 2. State Machine Integrity

**Mandatory Checks:**
- [ ] New states or transitions must be reflected in documentation.
- [ ] Transitions must be covered by integration tests.

## Pre-Commit Checklist

Before committing, verify:

**Code Quality:**
- [ ] Python formatting applied (PEP 8)
- [ ] Linting passes
- [ ] Type hints present
- [ ] Docstrings present

**Testing:**
- [ ] All unit tests pass: `pytest`
- [ ] Async tests use `@pytest.mark.asyncio`
- [ ] Mocking used for external API calls

**Documentation:**
- [ ] README updated for new features
- [ ] Architecture docs updated for design changes
- [ ] Implementation reference updated for new patterns

**Commit:**
- [ ] Commit message follows format: `type: description`
- [ ] Co-Authored-By trailer included

## See Also

- [AGENTS.md](../AGENTS.md) - Core A-E workflow
- [Universal DoD](system-prompts/principles/definition-of-done.md) - Agent Kernel universal requirements
- [Python DoD](system-prompts/languages/python/definition-of-done.md) - Agent Kernel language requirements
- [Architecture](architecture.md) - System design
- [Implementation Reference](implementation-reference.md) - Code patterns
- [Workflows](workflows.md) - Development workflows

---
Last Updated: 2026-02-01