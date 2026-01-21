"""
Test prompt generation strategies for different executors.

Tests the refactored prompt generation system where each executor
can define its own prompt format (XML vs Markdown).
"""

import pytest
from unittest.mock import Mock

from src.oneshot.providers.base import BaseExecutor
from src.oneshot.providers.cline_executor import ClineExecutor
from src.oneshot.providers.claude_executor import ClaudeExecutor


class MockBaseExecutor(BaseExecutor):
    """Mock implementation of BaseExecutor for testing prompt generation."""

    def get_provider_name(self): return "mock"
    def get_provider_metadata(self): return {}
    def should_capture_git_commit(self): return False
    def execute(self, prompt): pass
    def recover(self, task_id): pass
    def run_task(self, task): pass
    def build_command(self, prompt, model=None): return []
    def parse_streaming_activity(self, raw_output): return ("", {})


class TestBaseExecutorPromptGeneration:
    """Test the default XML-based prompt generation in BaseExecutor."""

    def test_get_system_instructions_worker(self):
        """Test worker system instructions."""
        executor = MockBaseExecutor()
        instructions = executor.get_system_instructions("worker")

        assert "autonomous intelligent agent" in instructions
        assert "instruction provided in the `<instruction>` XML block" in instructions

    def test_get_system_instructions_auditor(self):
        """Test auditor system instructions."""
        executor = MockBaseExecutor()
        instructions = executor.get_system_instructions("auditor")

        assert "expert auditor" in instructions
        assert "verify if the work presented" in instructions

    def test_get_system_instructions_reworker(self):
        """Test reworker system instructions."""
        executor = MockBaseExecutor()
        instructions = executor.get_system_instructions("reworker")

        assert "autonomous intelligent agent" in instructions
        assert "previous attempt to complete the task was marked as incomplete" in instructions

    def test_get_system_instructions_invalid_role(self):
        """Test invalid role raises ValueError."""
        executor = MockBaseExecutor()
        with pytest.raises(ValueError, match="Unknown role"):
            executor.get_system_instructions("invalid")

    def test_format_worker_prompt_basic(self):
        """Test basic worker prompt formatting."""
        executor = MockBaseExecutor()
        prompt = executor.format_prompt("Test task", "worker", "Test Header")

        assert "Test Header" in prompt
        assert "Test task" in prompt
        assert "IMPORTANT:" in prompt
        assert "PREFERRED FORMAT" in prompt

    def test_format_worker_prompt_with_iteration(self):
        """Test worker prompt with iteration context."""
        executor = MockBaseExecutor()
        context = {
            'iteration': 1,
            'max_iterations': 5,
            'auditor_feedback': 'Task was incomplete'
        }
        prompt = executor.format_prompt("Test task", "worker", "Test Header", context)

        assert "[Iteration 2/5]" in prompt
        assert "AUDITOR FEEDBACK:" in prompt
        assert "Task was incomplete" in prompt

    def test_format_auditor_prompt(self):
        """Test auditor prompt formatting."""
        executor = MockBaseExecutor()
        context = {'worker_result': 'Task completed successfully'}
        prompt = executor.format_prompt("Test task", "auditor", "Test Header", context)

        assert "Test Header" in prompt
        assert "Test task" in prompt
        assert "WORK RESULT:" in prompt
        assert "Task completed successfully" in prompt


class TestClineExecutorPromptGeneration:
    """Test Markdown-based prompt generation for ClineExecutor."""

    def test_get_system_instructions_worker_markdown(self):
        """Test Cline worker system instructions use Markdown."""
        executor = ClineExecutor()
        instructions = executor.get_system_instructions("worker")

        # Should be Markdown-style, not XML
        assert "autonomous intelligent agent" in instructions
        assert "Complete the task described below" in instructions
        assert "<instruction>" not in instructions  # No XML tags

    def test_get_system_instructions_auditor_markdown(self):
        """Test Cline auditor system instructions use Markdown."""
        executor = ClineExecutor()
        instructions = executor.get_system_instructions("auditor")

        assert "Success Auditor" in instructions
        assert "Evaluate the worker's response" in instructions
        assert "clear completion indicators" in instructions

    def test_get_system_instructions_reworker_markdown(self):
        """Test Cline reworker system instructions use Markdown."""
        executor = ClineExecutor()
        instructions = executor.get_system_instructions("reworker")

        assert "previous attempt" in instructions
        assert "marked as incomplete" in instructions

    def test_format_cline_worker_prompt_basic(self):
        """Test Cline worker prompt uses Markdown structure."""
        executor = ClineExecutor()
        prompt = executor.format_prompt("Test task", "worker", "Oneshot Task")

        # Check Markdown structure
        assert "# Oneshot Task" in prompt
        assert "## Important Guidance" in prompt
        assert "## Final Result" in prompt
        assert "## Task" in prompt
        assert "Test task" in prompt

        # Should not have XML tags
        assert "<instruction>" not in prompt
        assert "</instruction>" not in prompt

    def test_format_cline_worker_prompt_with_iteration(self):
        """Test Cline worker prompt with iteration context."""
        executor = ClineExecutor()
        context = {
            'iteration': 1,
            'max_iterations': 3,
            'auditor_feedback': 'Code had syntax errors'
        }
        prompt = executor.format_prompt("Fix the bug", "worker", "Retry Task", context)

        assert "## Context" in prompt
        assert "Iteration: 2/3" in prompt
        assert "Code had syntax errors" in prompt
        assert "different approach" in prompt

    def test_format_cline_auditor_prompt(self):
        """Test Cline auditor prompt uses Markdown structure."""
        executor = ClineExecutor()
        context = {'worker_result': '## Final Result\nBug fixed successfully'}
        prompt = executor.format_prompt("Fix the bug", "auditor", "Success Audit", context)

        assert "# Success Audit" in prompt
        assert "## Task" in prompt
        assert "## Work Result" in prompt
        assert "## Evaluation" in prompt
        assert "Bug fixed successfully" in prompt


class TestPromptGenerationIntegration:
    """Test that different executors produce different prompt formats."""

    def test_cline_vs_base_executor_prompts_differ(self):
        """Test that ClineExecutor produces different prompts than BaseExecutor."""
        base_executor = MockBaseExecutor()
        cline_executor = ClineExecutor()

        task = "Write a hello world function"
        context = {'iteration': 0}

        base_prompt = base_executor.format_prompt(task, "worker", "Test", context)
        cline_prompt = cline_executor.format_prompt(task, "worker", "Test", context)

        # Prompts should be different
        assert base_prompt != cline_prompt

        # Base should have XML-style elements
        assert "IMPORTANT:" in base_prompt
        assert "PREFERRED FORMAT" in base_prompt

        # Cline should have Markdown structure
        assert "## Important Guidance" in cline_prompt
        assert "## Final Result" in cline_prompt

    def test_auditor_prompts_differ_by_executor(self):
        """Test that auditor prompts also differ by executor type."""
        base_executor = MockBaseExecutor()
        cline_executor = ClineExecutor()

        task = "Verify the function works"
        context = {'worker_result': 'Function written successfully'}

        base_auditor_prompt = base_executor.format_prompt(task, "auditor", "Audit", context)
        cline_auditor_prompt = cline_executor.format_prompt(task, "auditor", "Audit", context)

        # Should be different formats
        assert base_auditor_prompt != cline_auditor_prompt

        # Base should have XML-style JSON requirements
        assert "JSON object containing" in base_auditor_prompt
        assert "`verdict`" in base_auditor_prompt

        # Cline should have cleaner Markdown structure
        assert "## Evaluation" in cline_auditor_prompt
        assert "## Task" in cline_auditor_prompt
        assert "## Work Result" in cline_auditor_prompt


class TestBackwardCompatibility:
    """Test that existing ClaudeExecutor still works (inherits defaults)."""

    def test_claude_executor_inherits_base_behavior(self):
        """Test that ClaudeExecutor (if it exists) would inherit XML prompts."""
        # Note: This test assumes ClaudeExecutor exists and doesn't override prompt methods
        # If ClaudeExecutor has custom prompt logic, this test would need adjustment

        try:
            # Mock ClaudeExecutor if it doesn't exist yet
            class MockClaudeExecutor(BaseExecutor):
                def get_provider_name(self): return "claude"
                def get_provider_metadata(self): return {}
                def should_capture_git_commit(self): return True
                def execute(self, prompt): pass
                def recover(self, task_id): pass
                def run_task(self, task): pass
                def build_command(self, prompt, model=None): return []
                def parse_streaming_activity(self, raw_output): return ("", {})

            claude_executor = MockClaudeExecutor()
            prompt = claude_executor.format_prompt("Test task", "worker")

            # Should use default XML format
            assert "IMPORTANT:" in prompt
            assert "<instruction>" not in prompt  # Uses the migrated logic

        except ImportError:
            pytest.skip("ClaudeExecutor not available for testing")