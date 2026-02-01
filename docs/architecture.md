# System Architecture

This document describes the architecture of oneshot.

## High-Level Architecture

oneshot is designed for autonomous task completion with auditor validation. It uses a state-machine based orchestrator to manage the interaction between a worker agent and an auditor agent.

```
┌─────────────────────────────────────┐
│             CLI / UI                │
├─────────────────────────────────────┤
│         Orchestrator (SM)           │
├──────────────┬──────────────────────┤
│    Worker    │       Auditor        │
└──────────────┴──────────────────────┘
```

## Project Structure

```
oneshot/
├── src/
│   ├── cli/             # CLI implementation
│   └── oneshot/         # Core logic
│       ├── core/        # Orchestrator, State Machine
│       ├── executors/   # Task execution engines (Aider, Claude, etc.)
│       └── protocol/    # Communication protocols
├── tests/               # Test suite
├── docs/                # Documentation
└── dev_notes/           # Change logs and plans
```

## Agent Kernel Integration

This architecture extends the Agent Kernel reference architecture. See:

- [Agent Kernel Reference Architecture](system-prompts/reference-architecture.md)

## See Also

- [AGENTS.md](../AGENTS.md) - Core workflow
- [Definition of Done](definition-of-done.md) - Quality standards
- [Implementation Reference](implementation-reference.md) - Implementation patterns
- [Workflows](workflows.md) - Development workflows

---
Last Updated: 2026-02-01
