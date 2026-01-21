import pytest
from src.oneshot.protocol import PromptGenerator, ResultSummary

def test_generate_worker_prompt_initial():
    generator = PromptGenerator()
    prompt = generator.generate_worker_prompt(
        oneshot_id="test-123",
        iteration=0,
        instruction="Fix the bug",
        system_prompt="You are a coder"
    )

    assert "<oneshot>test-123 worker #0</oneshot>" in prompt
    assert "You are a coder" in prompt
    assert "<instruction>" in prompt
    assert "Fix the bug" in prompt
    assert "</instruction>" in prompt
    assert "<auditor-feedback>" not in prompt

def test_generate_worker_prompt_reworker():
    generator = PromptGenerator()
    prompt = generator.generate_worker_prompt(
        oneshot_id="test-123",
        iteration=1,
        instruction="Fix the bug",
        system_prompt="You are a coder",
        auditor_feedback="Please add more tests",
        reworker_system_prompt="Try harder this time"
    )

    assert "<oneshot>test-123 worker #1</oneshot>" in prompt
    assert "<auditor-feedback>" in prompt
    assert "Please add more tests" in prompt
    assert "</auditor-feedback>" in prompt
    assert "<instruction>" in prompt
    assert "Fix the bug" in prompt
    assert "</instruction>" in prompt
    assert "Try harder this time" in prompt
    # Initial system prompt should be omitted or replaced in reworker flow according to requirements
    # "the reworker flow above, like this: ... <instruction> ... $reworker_system_prompt"
    assert "You are a coder" not in prompt 

def test_generate_auditor_prompt():
    generator = PromptGenerator()
    result_summary = ResultSummary(
        result="I fixed it.",
        leading_context=["Building...", "Testing..."],
        trailing_context=["Done."],
        score=20
    )

    prompt = generator.generate_auditor_prompt(
        oneshot_id="test-123",
        iteration=0,
        original_prompt="Fix the bug",
        result_summary=result_summary,
        auditor_system_prompt="Review this carefully"
    )

    assert "<oneshot>test-123 audit #0</oneshot>" in prompt
    assert "<what-was-requested>" in prompt
    assert "Fix the bug" in prompt
    assert "</what-was-requested>" in prompt
    assert "<worker-result>" in prompt
    assert "<leading-context>" in prompt
    assert "Building..." in prompt
    assert "Testing..." in prompt
    assert "</leading-context>" in prompt
    assert "I fixed it." in prompt
    assert "<trailing-context>" in prompt
    assert "Done." in prompt
    assert "</trailing-context>" in prompt
    assert "Review this carefully" in prompt

def test_generate_auditor_prompt_no_context():
    generator = PromptGenerator()
    result_summary = ResultSummary(result="Fixed.", score=10)
    
    prompt = generator.generate_auditor_prompt(
        oneshot_id="test-123",
        iteration=0,
        original_prompt="Task",
        result_summary=result_summary,
        auditor_system_prompt="Audit"
    )
    
    assert "<leading-context>" not in prompt
    assert "<trailing-context>" not in prompt
    assert "Fixed." in prompt

def test_prompt_truncation():
    generator = PromptGenerator(max_prompt_length=50)
    prompt = generator.generate_worker_prompt(
        oneshot_id="test-123",
        iteration=0,
        instruction="Very long instruction that exceeds fifty characters definitely",
        system_prompt="Sys"
    )
    
    assert len(prompt) <= 50 + len("... [TRUNCATED]")
    assert "[TRUNCATED]" in prompt
