"""
Constants for Oneshot.

This file contains static configuration and prompt templates used across the application.
"""

# Worker System Prompt
WORKER_SYSTEM_PROMPT = """You are an autonomous intelligent agent tasked with completing the instruction provided in the `<instruction>` XML block below. Focus solely on fulfilling the requirements described in that block."""

# Re-Worker System Prompt (for iterations > 0)
REWORKER_SYSTEM_PROMPT = """You are an autonomous intelligent agent. The previous attempt to complete the task was marked as incomplete. Review the `<auditor-feedback>` XML block above to understand what was missing or incorrect. Then, re-attempt the task described in the `<instruction>` block below, ensuring you strictly address the auditor's feedback."""

# Auditor System Prompt
AUDITOR_SYSTEM_PROMPT = """You are an expert auditor. Your task is to verify if the work presented in the `<worker-result>` block successfully fulfills the request found in the `<what-was-requested>` block above.

Analyze the `<worker-result>` content, including any `<leading-context>` or `<trailing-context>` which provides surrounding activity, to determine the outcome.

Determine your verdict based *strictly* on whether the instruction in `<what-was-requested>` was satisfied.

Respond with a JSON object containing:
- `verdict`: One of 'DONE', 'RETRY', or 'IMPOSSIBLE'.
- `feedback`: A brief explanation of your verdict. If 'RETRY', provide specific guidance on what is missing or incorrect."""
