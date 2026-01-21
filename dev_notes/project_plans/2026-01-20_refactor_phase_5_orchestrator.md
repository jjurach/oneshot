# Project Plan: Core Architecture Refactoring - Phase 5: The Orchestrator

## Overview
This final phase implements the `OnehotEngine` which ties all the components together. It replaces the imperative `run_oneshot` function with a main loop that delegates decisions to the State Machine and execution to the Executors/Pipeline.

## Related Documents
- `docs/streaming-and-state-management.md` (Architecture Specification)

## Objectives
- Implement the `OnehotEngine` class.
- Connect the Engine to the CLI.
- Remove legacy code.

## Components & Code Samples

### 1. `src/oneshot/engine.py`

**Concept:** The Main Loop (The "Pump").

```python
class OnehotEngine:
    def run(self):
        self.context.load()
        while True:
            state = self.context.current_state
            action = self.state_machine.get_next_action(state)
            
            if action.type == ActionType.EXIT:
                break
                
            elif action.type == ActionType.RUN_WORKER:
                try:
                    prompt = self.prompts.get_worker_prompt(self.context)
                    with self.executor.execute(prompt) as stream:
                        # Pump the pipeline
                        for event in self.pipeline.process(stream):
                            self.ui.render(event)
                            
                    # Normal completion
                    self.state_machine.transition(state, "success")
                    
                except InactivityTimeoutError:
                    self.state_machine.transition(state, "inactivity")
                    
                except KeyboardInterrupt:
                    self.state_machine.transition(state, "interrupt")
                    break
```

### 2. `src/cli/oneshot_cli.py`

**Concept:** Clean Entry Point.

```python
def main():
    args = parse_args()
    engine = OnehotEngine(
        executor=get_executor(args.executor),
        log_file=args.log_file
    )
    engine.run()
```

## Checklist
- [ ] Create `src/oneshot/engine.py`
- [ ] Implement `OnehotEngine` class
- [ ] Implement the Main Loop logic
- [ ] Implement `RECOVERY_PENDING` handling flow
- [ ] Implement `INTERRUPTED` handling flow
- [ ] Update `src/cli/oneshot_cli.py`
- [ ] Delete `run_oneshot` from `src/oneshot/oneshot.py`

## Test Plan: `tests/test_engine.py`

**Pattern:** Dependency Injection & Mocking.

```python
def test_engine_recovery_flow():
    # Setup: Mock everything
    sm = MockStateMachine()
    exec = MockExecutor()
    engine = OnehotEngine(sm, exec)
    
    # Scene 1: Worker Runs & Dies
    sm.next_action.return_value = Action(ActionType.RUN_WORKER)
    exec.execute.side_effect = InactivityTimeoutError()
    
    engine.step()
    
    # Assert: State transitioned to RECOVERY_PENDING
    assert sm.last_transition == "inactivity"
    
    # Scene 2: Recovery runs
    sm.current_state = OnehotState.RECOVERY_PENDING
    sm.next_action.return_value = Action(ActionType.RECOVER)
    exec.recover.return_value = RecoveryResult(success=True)
    
    engine.step()
    
    # Assert: State transitioned to AUDIT_PENDING
    assert sm.last_transition == "recovered"
```

- [ ] **Create `tests/test_engine.py`**
- [ ] **Integration Testing (Mocked):**
    - Verify the full "Happy Path" (Worker -> Audit -> Done).
    - Verify "Zombie Success" (Worker dies -> Recover -> Audit -> Done).
    - Verify "Interruption" (Ctrl-C -> State Saved -> Resume).
- [ ] **System Testing:**
    - Run the actual CLI against a dummy agent to verify end-to-end functionality.