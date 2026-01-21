import asyncio
import json
import re
from contextlib import contextmanager
from typing import Dict, List, Optional, Tuple, Generator, Any

from src.oneshot.providers.base import BaseExecutor, RecoveryResult, ExecutionResult

class MockExecutor(BaseExecutor):
    """A mock executor for testing purposes."""

    def __init__(self, executor_type: str, output_generator_type: str = "text", simulate_error: bool = False,
                 simulated_exit_code: int = 0, simulated_git_hash: Optional[str] = None,
                 simulated_recover_success: bool = False, simulated_recovered_activity: Optional[List[Any]] = None,
                 simulated_verdict: Optional[str] = None, simulate_inactivity: bool = False,
                 inactivity_timeout: float = 1.0):
        """
        Initialize the mock executor.

        Args:
            executor_type: The type of executor (e.g., "mock", "gemini", "claude").
            output_generator_type: Type of output to generate ("text", "json", "mixed", "empty").
            simulate_error: If True, the executor will simulate an error.
            simulated_exit_code: The exit code to return if simulate_error is False.
            simulated_git_hash: A simulated git commit hash to return.
            simulated_recover_success: Whether the recover method should succeed.
            simulated_recovered_activity: List of activities to return from recover.
            simulated_verdict: Verdict for recovery.
            simulate_inactivity: If True, simulate an inactivity timeout.
            inactivity_timeout: Timeout duration for inactivity simulation.
        """
        self.executor_type = executor_type
        self.output_generator_type = output_generator_type
        self.simulate_error = simulate_error
        self.simulated_exit_code = simulated_exit_code
        self.simulated_git_hash = simulated_git_hash
        self.simulated_recover_success = simulated_recover_success
        self.simulated_recovered_activity = simulated_recovered_activity if simulated_recovered_activity is not None else []
        self.simulated_verdict = simulated_verdict
        self.simulate_inactivity = simulate_inactivity
        self.inactivity_timeout = inactivity_timeout
        self._prompt = ""
        self._process = None # Mock process
        self._last_activity = asyncio.get_event_loop().time() # For inactivity simulation

    @contextmanager
    def execute(self, prompt: str) -> Generator[str, None, None]:
        """
        Simulates executing a task and yielding streaming output.
        """
        self._prompt = prompt
        self._last_activity = asyncio.get_event_loop().time()

        if self.simulate_inactivity:
            asyncio.sleep(self.inactivity_timeout + 0.1) # Sleep longer than timeout
            # This sleep will cause the InactivityMonitor to detect timeout
            # In a real scenario, the pipeline would handle this.
            # For mocking, we can just yield nothing or a specific message.
            yield "" # Yield empty to signify no activity

        elif self.simulate_error:
            # Simulate an error during execution
            raise RuntimeError(f"Mock executor '{self.executor_type}' failed to execute.")
        else:
            # Yield simulated output based on generator type
            for line in self._generate_output():
                self._last_activity = asyncio.get_event_loop().time() # Update activity
                yield line
            # Simulate process exit code if needed (not directly visible in generator, but assumed)

    def _generate_output(self) -> List[str]:
        """Generates simulated output lines."""
        if self.output_generator_type == "text":
            return [
                "Processing task...",
                "Step 1 complete.",
                "Step 2 complete.",
                "Task finished.",
                f"Result: Success for prompt '{self._prompt}'",
                "DONE"
            ]
        elif self.output_generator_type == "json":
            return [
                '{"event": "processing", "step": 1}',
                '{"event": "progress", "percentage": 50}',
                '{"event": "done", "result": {"status": "success", "message": "Task completed", "data": {"key": "value"}}}'
            ]
        elif self.output_generator_type == "mixed":
            return [
                "Starting task...",
                '{"event": "progress", "percentage": 25}',
                "Doing some work...",
                '{"event": "intermediate_result", "details": "some details here"}',
                "Almost there...",
                '{"event": "done", "result": {"status": "success", "summary": "Task finished successfully"}}'
            ]
        elif self.output_generator_type == "empty":
            return []
        else:
            return ["Unknown output type."]

    def recover(self, task_id: str) -> RecoveryResult:
        """
        Simulates recovery logic.
        """
        return RecoveryResult(
            success=self.simulated_recover_success,
            recovered_activity=self.simulated_recovered_activity,
            verdict=self.simulated_verdict
        )

    def run_task(self, task: str) -> ExecutionResult:
        """
        Simulates running a task and returning a result.
        """
        if self.simulate_error:
            return ExecutionResult(success=False, output="", error="Mock execution error")
        else:
            output_lines = self._generate_output()
            full_output = "\n".join(output_lines)
            return ExecutionResult(
                success=True,
                output=full_output,
                git_commit_hash=self.simulated_git_hash,
                metadata={"exit_code": self.simulated_exit_code}
            )

    def build_command(self, prompt: str, model: Optional[str] = None) -> List[str]:
        """
        Simulates building a command.
        """
        command = ["mock_cli", "--prompt", prompt]
        if model:
            command.extend(["--model", model])
        return command

    def parse_streaming_activity(self, raw_output: str) -> Tuple[str, Dict[str, Any]]:
        """
        Simulates parsing streaming activity.
        Returns a dummy summary and metadata.
        """
        # In a real scenario, this would parse JSON/text to extract structured data.
        # For the mock, we return a simplified representation.
        summary = f"Mock executor '{self.executor_type}' processed: '{raw_output[:50]}...'"
        metadata = {
            "executor_type": self.executor_type,
            "parsed_lines": len(raw_output.splitlines()),
            "simulated_git_hash": self.simulated_git_hash if self.should_capture_git_commit() else None
        }
        return summary, metadata

    def get_provider_name(self) -> str:
        """Returns the mock executor's type name."""
        return self.executor_type

    def get_provider_metadata(self) -> Dict[str, Any]:
        """Returns mock metadata."""
        return {
            "type": self.executor_type,
            "capabilities": ["streaming", "command_building"],
            "supports_model_selection": True if self.executor_type in ["gemini", "claude"] else False,
        }

    def should_capture_git_commit(self) -> bool:
        """Mock logic for git commit capture."""
        return self.executor_type in ["mock_git_executor", "mock_claude", "mock_aider"]

    @property
    def process(self):
        """Mock process attribute."""
        # In a real scenario, this would be a subprocess.Popen object
        return None # Indicate no real process

    @property
    def last_activity(self):
        """Mock last activity attribute."""
        return self._last_activity
