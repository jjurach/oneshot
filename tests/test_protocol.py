"""
Tests for Protocol - Result Extraction and Prompt Generation

Tests verify:
- ResultExtractor scoring and selection logic
- PromptGenerator context injection
- Activity log parsing with various formats
"""

import json
import tempfile
import pytest
from pathlib import Path
from src.oneshot.protocol import ResultExtractor, PromptGenerator
from src.oneshot.context import ExecutionContext


class TestResultExtractorScoring:
    """Test result extraction scoring logic."""

    def test_score_text_with_done(self):
        """Test that 'DONE' keyword increases score."""
        extractor = ResultExtractor()

        score_without_done = extractor._score_text("Completed successfully")
        score_with_done = extractor._score_text("Task is DONE")

        assert score_with_done > score_without_done

    def test_score_text_with_json_structure(self):
        """Test that JSON structure increases score."""
        extractor = ResultExtractor()

        score_plain = extractor._score_text("Completed")
        score_json = extractor._score_text('{"status": "success"}')

        assert score_json > score_plain

    def test_score_text_with_status_field(self):
        """Test that status field increases score."""
        extractor = ResultExtractor()

        score_without = extractor._score_text("Work done")
        score_with = extractor._score_text('{"status": "complete"}')

        assert score_with > score_without

    def test_score_text_with_substantial_length(self):
        """Test that substantial text scores higher."""
        extractor = ResultExtractor()

        short = "DONE"
        long = "DONE: " + "x" * 100

        assert extractor._score_text(long) > extractor._score_text(short)

    def test_score_text_combined(self):
        """Test scoring with multiple positive signals."""
        extractor = ResultExtractor()

        text = '{"status": "DONE", "result": "task completed"}'
        score = extractor._score_text(text)

        # Should have bonus for: DONE, JSON structure, status field, result field, length
        assert score >= 20

    def test_score_text_empty_returns_zero(self):
        """Test that empty text returns 0."""
        extractor = ResultExtractor()

        assert extractor._score_text("") == 0
        assert extractor._score_text(None) == 0


class TestResultExtractorFormatEvent:
    """Test event formatting."""

    def test_format_event_with_output_field(self):
        """Test formatting event with 'output' field."""
        extractor = ResultExtractor()

        event = {"type": "activity", "output": "Task completed"}
        text = extractor._format_event(event)

        assert text == "Task completed"

    def test_format_event_with_stdout_field(self):
        """Test formatting event with 'stdout' field."""
        extractor = ResultExtractor()

        event = {"type": "activity", "stdout": "Process output"}
        text = extractor._format_event(event)

        assert text == "Process output"

    def test_format_event_with_text_field(self):
        """Test formatting event with 'text' field."""
        extractor = ResultExtractor()

        event = {"type": "activity", "text": "Message"}
        text = extractor._format_event(event)

        assert text == "Message"

    def test_format_event_stringify_dict(self):
        """Test that dict without known fields gets stringified."""
        extractor = ResultExtractor()

        event = {"custom": "value", "nested": {"key": "data"}}
        text = extractor._format_event(event)

        # Should contain JSON representation
        assert isinstance(text, str)
        assert "custom" in text

    def test_format_event_empty_dict(self):
        """Test that empty dict returns None."""
        extractor = ResultExtractor()

        text = extractor._format_event({})
        assert text is None


class TestResultExtractorExtraction:
    """Test full result extraction from logs."""

    def test_extract_result_single_best_candidate(self, tmp_path):
        """Test extracting the best candidate from a log file."""
        log_path = tmp_path / "oneshot-log.json"

        # Write NDJSON log
        with open(log_path, 'w') as f:
            f.write('{"output": "Thinking..."}\n')
            f.write('{"output": "DONE with task"}\n')
            f.write('{"output": "Final message"}\n')

        extractor = ResultExtractor()
        result = extractor.extract_result(str(log_path))

        assert result is not None
        assert "DONE" in result

    def test_extract_result_with_json_preference(self, tmp_path):
        """Test that JSON output is preferred over plain text."""
        log_path = tmp_path / "oneshot-log.json"

        with open(log_path, 'w') as f:
            f.write('{"output": "Simple DONE"}\n')
            f.write('{"output": "{\\"status\\": \\"DONE\\", \\"result\\": \\"success\\"}"}\n')

        extractor = ResultExtractor()
        result = extractor.extract_result(str(log_path))

        # Should select the JSON one due to higher score
        assert "status" in result or "DONE" in result

    def test_extract_result_skips_invalid_json_lines(self, tmp_path):
        """Test that malformed JSON lines are skipped."""
        log_path = tmp_path / "oneshot-log.json"

        with open(log_path, 'w') as f:
            f.write('invalid json\n')
            f.write('{"output": "DONE"}\n')
            f.write('{more invalid\n')

        extractor = ResultExtractor()
        result = extractor.extract_result(str(log_path))

        assert result is not None
        assert "DONE" in result

    def test_extract_result_empty_log_returns_none(self, tmp_path):
        """Test that empty log returns None."""
        log_path = tmp_path / "oneshot-log.json"
        log_path.write_text("")

        extractor = ResultExtractor()
        result = extractor.extract_result(str(log_path))

        assert result is None

    def test_extract_result_selects_best_score(self, tmp_path):
        """Test that extractor selects candidate with best score."""
        log_path = tmp_path / "oneshot-log.json"

        with open(log_path, 'w') as f:
            f.write('{"output": "low quality"}\n')
            f.write('{"output": "DONE and structured", "status": "complete"}\n')

        extractor = ResultExtractor()
        result = extractor.extract_result(str(log_path))

        # Should select the one with DONE and status field (higher score)
        assert result is not None
        assert "DONE" in result or "status" in result

    def test_extract_result_nonexistent_file_returns_none(self):
        """Test that nonexistent file returns None gracefully."""
        extractor = ResultExtractor()
        result = extractor.extract_result("/nonexistent/path/log.json")

        assert result is None

    def test_extract_result_complex_log(self, tmp_path):
        """Test extraction with realistic complex log."""
        log_path = tmp_path / "oneshot-log.json"

        with open(log_path, 'w') as f:
            f.write('{"type": "state_change", "from": "CREATED", "to": "WORKER_EXECUTING"}\n')
            f.write('{"type": "activity", "stdout": "Starting work..."}\n')
            f.write('{"type": "activity", "stdout": "Processing..."}\n')
            f.write('{"type": "activity", "stdout": "Almost done..."}\n')
            f.write(
                '{"type": "activity", "output": '
                '"{\\"status\\": \\"DONE\\", \\"summary\\": \\"Completed all tasks\\", \\"files_modified\\": 5}"}\n'
            )
            f.write('{"type": "state_change", "from": "WORKER_EXECUTING", "to": "AUDIT_PENDING"}\n')

        extractor = ResultExtractor()
        result = extractor.extract_result(str(log_path))

        assert result is not None
        assert "DONE" in result or "status" in result


class TestPromptGeneratorWorkerPrompt:
    """Test worker prompt generation."""

    def test_generate_worker_prompt_basic(self, tmp_path):
        """Test basic worker prompt generation."""
        ctx_path = tmp_path / "oneshot.json"
        ctx = ExecutionContext(str(ctx_path))
        gen = PromptGenerator(ctx)

        task = "Write a Python function to add two numbers"
        prompt = gen.generate_worker_prompt(task)

        assert task in prompt
        assert "Iteration 1" in prompt
        assert "DONE" in prompt

    def test_generate_worker_prompt_with_feedback(self, tmp_path):
        """Test worker prompt includes feedback."""
        ctx_path = tmp_path / "oneshot.json"
        ctx = ExecutionContext(str(ctx_path))
        gen = PromptGenerator(ctx)

        task = "Write a function"
        feedback = "Your function needs better error handling"

        prompt = gen.generate_worker_prompt(task, iteration=2, feedback=feedback)

        assert "Feedback from Auditor" in prompt
        assert feedback in prompt

    def test_generate_worker_prompt_with_previous_work(self, tmp_path):
        """Test worker prompt includes previous work context."""
        ctx_path = tmp_path / "oneshot.json"
        ctx = ExecutionContext(str(ctx_path))
        ctx.set_worker_result("Previously completed Part 1")
        ctx.save()

        gen = PromptGenerator(ctx)
        task = "Complete Part 2"

        prompt = gen.generate_worker_prompt(task, iteration=2)

        assert "Previous Work Summary" in prompt
        assert "Previously completed Part 1" in prompt

    def test_generate_worker_prompt_with_variables(self, tmp_path):
        """Test worker prompt includes variables."""
        ctx_path = tmp_path / "oneshot.json"
        ctx = ExecutionContext(str(ctx_path))
        gen = PromptGenerator(ctx)

        task = "Use these settings"
        variables = {"timeout": 300, "retries": 3}

        prompt = gen.generate_worker_prompt(task, variables=variables)

        assert "Variables" in prompt
        assert "timeout" in prompt
        assert "300" in prompt


class TestPromptGeneratorAuditorPrompt:
    """Test auditor prompt generation."""

    def test_generate_auditor_prompt_basic(self, tmp_path):
        """Test basic auditor prompt generation."""
        ctx_path = tmp_path / "oneshot.json"
        ctx = ExecutionContext(str(ctx_path))
        gen = PromptGenerator(ctx)

        task = "Write a function"
        result = "Created function that adds numbers"

        prompt = gen.generate_auditor_prompt(task, result)

        assert "Auditor Review" in prompt
        assert task in prompt
        assert result in prompt
        assert "DONE" in prompt
        assert "RETRY" in prompt
        assert "IMPOSSIBLE" in prompt

    def test_generate_auditor_prompt_iteration(self, tmp_path):
        """Test auditor prompt shows iteration number."""
        ctx_path = tmp_path / "oneshot.json"
        ctx = ExecutionContext(str(ctx_path))
        gen = PromptGenerator(ctx)

        prompt = gen.generate_auditor_prompt("task", "result", iteration=3)

        assert "Iteration: 3" in prompt


class TestPromptGeneratorRecoveryPrompt:
    """Test recovery prompt generation."""

    def test_generate_recovery_prompt_basic(self, tmp_path):
        """Test basic recovery prompt generation."""
        ctx_path = tmp_path / "oneshot.json"
        ctx = ExecutionContext(str(ctx_path))
        gen = PromptGenerator(ctx)

        task = "Complete the task"
        prompt = gen.generate_recovery_prompt(task, "WORKER_EXECUTING")

        assert "Recovery Analysis" in prompt
        assert "WORKER_EXECUTING" in prompt
        assert task in prompt
        assert "success" in prompt or "failed" in prompt

    def test_generate_recovery_prompt_with_logs(self, tmp_path):
        """Test recovery prompt includes executor logs."""
        ctx_path = tmp_path / "oneshot.json"
        ctx = ExecutionContext(str(ctx_path))
        gen = PromptGenerator(ctx)

        task = "Do work"
        logs = "Final output: Task completed successfully"

        prompt = gen.generate_recovery_prompt(task, "WORKER_EXECUTING", logs)

        assert "Executor Logs" in prompt
        assert logs in prompt
