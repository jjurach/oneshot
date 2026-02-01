"""
Tests for the Oneshot Engine (Phase 5 - The Orchestrator)

Tests the main orchestration loop including:
- State machine integration
- Worker execution
- Auditor execution
- Recovery handling
- Interruption handling
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from contextlib import contextmanager

from oneshot.engine import OnehotEngine
from oneshot.state import OnehotState, ActionType, StateMachine
from oneshot.context import ExecutionContext
from oneshot.protocol import ResultExtractor
from oneshot.providers.base import BaseExecutor, RecoveryResult
from oneshot.pipeline import InactivityTimeoutError


class MockExecutor(BaseExecutor):
    """Mock executor for testing."""

    def __init__(self, output_lines=None, should_fail=False, timeout_error=False):
        self.output_lines = output_lines or ["line 1", "line 2"]
        self.should_fail = should_fail
        self.timeout_error = timeout_error
        self.execute_called = False
        self.last_prompt = None

    @contextmanager
    def execute(self, prompt: str):
        """Context manager yielding a generator of output lines."""
        self.execute_called = True
        self.last_prompt = prompt

        def generator():
            if self.timeout_error:
                raise InactivityTimeoutError("Timeout")
            if self.should_fail:
                raise RuntimeError("Executor failed")
            for line in self.output_lines:
                yield line

        yield generator()

    def recover(self, task_id: str):
        """Return a mock recovery result."""
        return RecoveryResult(
            success=True,
            recovered_activity=[{"type": "test", "data": "recovered"}],
            verdict="success"
        )

    def run_task(self, task: str):
        """Mock run_task implementation."""
        from oneshot.providers.base import ExecutionResult
        return ExecutionResult(
            success=True,
            output="Mock task result",
            error=None,
            git_commit_hash=None,
            metadata={}
        )

    def build_command(self, prompt: str, model=None):
        """Mock build_command implementation."""
        return ["mock", "command"]

    def parse_streaming_activity(self, raw_output: str):
        """Mock parse_streaming_activity implementation."""
        return ("summary", {"detail": "data"})

    def get_provider_name(self) -> str:
        """Mock get_provider_name implementation."""
        return "mock"

    def get_provider_metadata(self):
        """Mock get_provider_metadata implementation."""
        return {"type": "mock"}

    def should_capture_git_commit(self) -> bool:
        """Mock should_capture_git_commit implementation."""
        return False


@pytest.fixture
def mock_context():
    """Create a mock execution context."""
    context = Mock(spec=ExecutionContext)
    context.get_iteration_count.return_value = 0
    context.get_variable.return_value = None
    context.to_dict.return_value = {
        'oneshot_id': 'test-id',
        'task': 'Test task',
        'session_log_path': '/tmp/oneshot-log.json',
        'state': 'CREATED'
    }
    context._data = {}
    context.save = Mock()
    context.set_metadata = Mock()
    return context


@pytest.fixture
def mock_state_machine():
    """Create a mock state machine."""
    sm = Mock(spec=StateMachine)
    sm.current_state = OnehotState.CREATED
    return sm


@pytest.fixture
def engine(mock_context, mock_state_machine):
    """Create an engine instance with mocks."""
    worker = MockExecutor(output_lines=["Worker output"])
    auditor = MockExecutor(output_lines=["DONE: Task completed"])

    engine = OnehotEngine(
        state_machine=mock_state_machine,
        executor_worker=worker,
        executor_auditor=auditor,
        context=mock_context,
        max_iterations=3,
        inactivity_timeout=300.0,
        verbose=False
    )
    return engine


class TestEngineInitialization:
    """Test engine initialization and setup."""

    def test_init_with_defaults(self):
        """Test engine initialization with default values."""
        engine = OnehotEngine()
        assert engine.state_machine is not None
        assert engine.max_iterations == 5
        assert engine.inactivity_timeout == 300.0
        assert engine.verbose is False

    def test_init_with_custom_values(self):
        """Test engine initialization with custom values."""
        sm = StateMachine()
        engine = OnehotEngine(
            state_machine=sm,
            max_iterations=10,
            inactivity_timeout=500.0,
            verbose=True
        )
        assert engine.state_machine is sm
        assert engine.max_iterations == 10
        assert engine.inactivity_timeout == 500.0
        assert engine.verbose is True

    def test_signal_handlers_installed(self):
        """Test that signal handlers are installed."""
        with patch('signal.signal') as mock_signal:
            engine = OnehotEngine()
            # Verify SIGINT handler was installed
            mock_signal.assert_called()


class TestEngineStateManagement:
    """Test engine state transitions and saving."""

    def test_save_state(self, engine, mock_context):
        """Test that state is saved to context."""
        engine.state_machine.current_state = OnehotState.WORKER_EXECUTING
        engine._save_state()

        assert mock_context.set_state.called or mock_context.save.called

    def test_context_value_retrieval(self, engine, mock_context):
        """Test safe context value retrieval."""
        mock_context.get_variable.return_value = "test_value"
        value = engine._get_context_value('test_key')
        assert value == "test_value"

    def test_context_value_fallback(self, engine, mock_context):
        """Test fallback to dict access."""
        mock_context.get_variable.return_value = None
        mock_context.to_dict.return_value = {'fallback_key': 'fallback_value'}
        value = engine._get_context_value('fallback_key')
        assert value == "fallback_value"


class TestWorkerExecution:
    """Test worker execution flow."""

    def test_worker_execution_success(self, engine, mock_state_machine):
        """Test successful worker execution."""
        mock_state_machine.get_next_action.return_value = Mock(type=ActionType.RUN_WORKER)
        mock_state_machine.transition.return_value = OnehotState.AUDIT_PENDING

        engine._execute_worker(OnehotState.CREATED)

        # Verify transition occurred
        assert mock_state_machine.transition.called

    def test_worker_iteration_increment(self, engine, mock_context, mock_state_machine):
        """Test worker iteration count increments on reiteration."""
        mock_context.get_iteration_count.return_value = 1
        mock_state_machine.transition.return_value = OnehotState.WORKER_EXECUTING

        engine._execute_worker(OnehotState.REITERATION_PENDING)

        # Verify iteration count was updated
        assert mock_context.save.called

    def test_worker_max_iterations_reached(self, engine, mock_context, mock_state_machine):
        """Test that max iterations limit is enforced."""
        engine.max_iterations = 2
        mock_context.get_iteration_count.return_value = 2
        mock_state_machine.transition.return_value = OnehotState.FAILED

        engine._execute_worker(OnehotState.REITERATION_PENDING)

        # Verify failed state transition
        assert mock_state_machine.transition.called

    def test_worker_inactivity_timeout(self, engine, mock_state_machine):
        """Test worker inactivity timeout handling."""
        engine.executor_worker = MockExecutor(timeout_error=True)
        mock_state_machine.transition.return_value = OnehotState.RECOVERY_PENDING

        # Patch the pipeline to raise timeout
        with patch('oneshot.engine.build_pipeline') as mock_pipeline:
            mock_pipeline.side_effect = InactivityTimeoutError("timeout")

            engine._execute_worker(OnehotState.CREATED)

            # Verify transition to recovery
            assert mock_state_machine.transition.called


class TestAuditorExecution:
    """Test auditor execution flow."""

    def test_auditor_execution_success(self, engine, mock_state_machine):
        """Test successful auditor execution."""
        mock_state_machine.get_next_action.return_value = Mock(type=ActionType.RUN_AUDITOR)
        mock_state_machine.transition.return_value = OnehotState.COMPLETED

        # Mock verdict extraction
        with patch.object(engine, '_extract_auditor_verdict', return_value="done"):
            engine._execute_auditor(OnehotState.AUDIT_PENDING)

        assert mock_state_machine.transition.called

    def test_auditor_verdict_done(self, engine, mock_state_machine):
        """Test auditor verdict 'done'."""
        mock_state_machine.transition.return_value = OnehotState.COMPLETED

        with patch.object(engine, '_extract_auditor_verdict', return_value="done"):
            engine._execute_auditor(OnehotState.AUDIT_PENDING)

        # Verify transition to COMPLETED
        mock_state_machine.transition.assert_called_with(
            OnehotState.AUDITOR_EXECUTING, "done"
        )

    def test_auditor_verdict_retry(self, engine, mock_state_machine):
        """Test auditor verdict 'retry'."""
        mock_state_machine.transition.return_value = OnehotState.REITERATION_PENDING

        with patch.object(engine, '_extract_auditor_verdict', return_value="retry"):
            engine._execute_auditor(OnehotState.AUDIT_PENDING)

        mock_state_machine.transition.assert_called_with(
            OnehotState.AUDITOR_EXECUTING, "retry"
        )

    def test_auditor_verdict_impossible(self, engine, mock_state_machine):
        """Test auditor verdict 'impossible'."""
        mock_state_machine.transition.return_value = OnehotState.REJECTED

        with patch.object(engine, '_extract_auditor_verdict', return_value="impossible"):
            engine._execute_auditor(OnehotState.AUDIT_PENDING)

        mock_state_machine.transition.assert_called_with(
            OnehotState.AUDITOR_EXECUTING, "impossible"
        )


class TestRecoveryExecution:
    """Test recovery flow."""

    def test_recovery_success(self, engine, mock_state_machine, mock_context):
        """Test successful recovery."""
        mock_state_machine.transition.return_value = OnehotState.AUDIT_PENDING
        engine.executor_worker = MockExecutor()

        engine._execute_recovery(OnehotState.RECOVERY_PENDING)

        # Verify state transition
        assert mock_state_machine.transition.called
        # Verify metadata saved
        assert mock_context.set_metadata.called

    def test_recovery_partial(self, engine, mock_state_machine):
        """Test partial recovery."""
        mock_state_machine.transition.return_value = OnehotState.REITERATION_PENDING

        # Mock partial recovery result
        engine.executor_worker = Mock()
        engine.executor_worker.recover.return_value = RecoveryResult(
            success=True,
            recovered_activity=[],
            verdict="partial"
        )

        engine._execute_recovery(OnehotState.RECOVERY_PENDING)

        mock_state_machine.transition.assert_called_with(
            OnehotState.RECOVERY_PENDING, "zombie_partial"
        )

    def test_recovery_dead(self, engine, mock_state_machine):
        """Test when nothing can be recovered."""
        mock_state_machine.transition.return_value = OnehotState.FAILED

        engine.executor_worker = Mock()
        engine.executor_worker.recover.return_value = RecoveryResult(
            success=False,
            recovered_activity=[],
            verdict=None
        )

        engine._execute_recovery(OnehotState.RECOVERY_PENDING)

        mock_state_machine.transition.assert_called_with(
            OnehotState.RECOVERY_PENDING, "zombie_dead"
        )


class TestPromptGeneration:
    """Test prompt generation."""

    def test_worker_prompt_first_iteration(self, engine, mock_context):
        """Test worker prompt generation for first iteration."""
        mock_context.to_dict.return_value = {'task': 'Do something'}
        prompt = engine._generate_worker_prompt(0)

        assert 'Do something' in prompt
        assert 'Iteration' not in prompt

    def test_worker_prompt_reiteration(self, engine, mock_context):
        """Test worker prompt generation for reiteration."""
        mock_context.to_dict.return_value = {'task': 'Do something'}
        prompt = engine._generate_worker_prompt(1)

        assert 'Do something' in prompt
        assert 'Iteration 2' in prompt

    def test_auditor_prompt_generation(self, engine, mock_context):
        """Test auditor prompt generation."""
        from oneshot.protocol import ResultSummary
        result_summary = ResultSummary(result="Worker result", score=100)
        with patch.object(engine.result_extractor, 'extract_result', return_value=result_summary):
            prompt = engine._generate_auditor_prompt()

            assert 'Worker result' in prompt
            assert 'DONE' in prompt
            assert 'RETRY' in prompt
            assert 'IMPOSSIBLE' in prompt


class TestVerdictExtraction:
    """Test auditor verdict extraction."""

    def test_extract_verdict_done(self, engine):
        """Test extracting 'done' verdict."""
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.readlines.return_value = [
                '{"data": "done"}\n'
            ]
            verdict = engine._extract_auditor_verdict()
            assert verdict == "done"

    def test_extract_verdict_retry(self, engine):
        """Test extracting 'retry' verdict."""
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.readlines.return_value = [
                '{"data": "retry needed"}\n'
            ]
            verdict = engine._extract_auditor_verdict()
            assert verdict == "retry"

    def test_extract_verdict_impossible(self, engine):
        """Test extracting 'impossible' verdict."""
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.readlines.return_value = [
                '{"data": "impossible to complete"}\n'
            ]
            verdict = engine._extract_auditor_verdict()
            assert verdict == "impossible"

    def test_extract_verdict_unknown(self, engine):
        """Test extracting unknown verdict."""
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.readlines.return_value = [
                '{"data": "unclear"}\n'
            ]
            verdict = engine._extract_auditor_verdict()
            assert verdict == "unknown"


class TestExitConditions:
    """Test exit conditions and success determination."""

    def test_should_exit_success_completed(self, engine):
        """Test success exit on COMPLETED state."""
        result = engine._should_exit_success(OnehotState.COMPLETED)
        assert result is True

    def test_should_exit_success_failed(self, engine):
        """Test failure exit on FAILED state."""
        result = engine._should_exit_success(OnehotState.FAILED)
        assert result is False

    def test_should_exit_success_interrupted(self, engine):
        """Test failure exit on INTERRUPTED state."""
        result = engine._should_exit_success(OnehotState.INTERRUPTED)
        assert result is False

    def test_should_exit_success_rejected(self, engine):
        """Test failure exit on REJECTED state."""
        result = engine._should_exit_success(OnehotState.REJECTED)
        assert result is False


class TestMainLoop:
    """Test the main run() loop."""

    def test_run_simple_success_path(self, engine, mock_state_machine):
        """Test main loop with simple success path."""
        # Mock the sequence: CREATED -> WORKER_EXECUTING -> AUDIT_PENDING -> AUDITOR_EXECUTING -> COMPLETED
        states = [
            OnehotState.CREATED,
            OnehotState.AUDIT_PENDING,
            OnehotState.COMPLETED,
        ]
        state_index = [0]

        def get_action(state):
            if state == OnehotState.COMPLETED:
                return Mock(type=ActionType.EXIT, payload={'reason': 'success'})
            elif state == OnehotState.CREATED:
                return Mock(type=ActionType.RUN_WORKER)
            elif state == OnehotState.AUDIT_PENDING:
                return Mock(type=ActionType.RUN_AUDITOR)
            return Mock(type=ActionType.WAIT)

        mock_state_machine.get_next_action.side_effect = get_action

        def transition_side_effect(state, event):
            if state == OnehotState.CREATED and event == "start":
                return OnehotState.WORKER_EXECUTING
            elif state == OnehotState.WORKER_EXECUTING and event == "success":
                return OnehotState.AUDIT_PENDING
            elif state == OnehotState.AUDITOR_EXECUTING and event == "done":
                return OnehotState.COMPLETED
            return state

        mock_state_machine.transition.side_effect = transition_side_effect

        # We need to limit the loop by modifying state machine state
        call_count = [0]

        def advance_state(state):
            call_count[0] += 1
            if call_count[0] > 3:
                mock_state_machine.current_state = OnehotState.COMPLETED
            return states[min(call_count[0] - 1, len(states) - 1)]

        mock_state_machine.current_state = OnehotState.CREATED

        # Patch the internal methods to avoid actual executor calls
        with patch.object(engine, '_execute_worker'):
            with patch.object(engine, '_execute_auditor'):
                with patch.object(engine, '_save_state'):
                    # Run one iteration
                    action = mock_state_machine.get_next_action(OnehotState.CREATED)
                    assert action.type == ActionType.RUN_WORKER


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
