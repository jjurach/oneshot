"""
Protocol - Result Extraction and Prompt Generation

This module provides:
1. ResultExtractor: Parses activity logs and extracts the "best" result
2. PromptGenerator: Injects context into prompts for the Worker and Auditor
"""

import json
from typing import List, Tuple, Optional, Dict, Any
import re


class ResultExtractor:
    """
    Extracts "Full Text" results from activity logs.

    Processes noisy log streams and identifies high-quality output by
    scoring candidates based on heuristics (presence of "DONE", JSON structure, etc.).
    """

    def __init__(self):
        """Initialize the result extractor."""
        self.score_weights = {
            'done_keyword': 10,
            'json_structure': 5,
            'substantial_length': 3,
            'status_field': 8,
            'result_field': 5,
        }

    def extract_result(self, log_path: str) -> Optional[str]:
        """
        Extract the best result from a log file.

        Args:
            log_path: Path to oneshot-log.json (NDJSON format)

        Returns:
            The best scored output text, or None if no valid content found
        """
        candidates: List[Tuple[int, str]] = []

        try:
            with open(log_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        event = json.loads(line)
                        text = self._format_event(event)
                        if text:
                            score = self._score_text(text)
                            if score > 0:
                                candidates.append((score, text))
                    except json.JSONDecodeError:
                        # Skip malformed JSON lines
                        continue

        except FileNotFoundError:
            return None
        except Exception:
            return None

        if not candidates:
            return None

        # Sort by score (descending) and return the best
        best_score, best_text = sorted(candidates, reverse=True)[0]
        return best_text

    def _format_event(self, event: Dict[str, Any]) -> Optional[str]:
        """
        Format an event object into a text representation.

        Args:
            event: A parsed JSON event from the log

        Returns:
            Formatted text, or None if the event is not useful
        """
        # Extract text from various possible event structures
        if isinstance(event, dict):
            # Check for common output fields
            for field_name in ['output', 'stdout', 'text', 'content', 'message', 'data']:
                if field_name in event and event[field_name]:
                    return str(event[field_name])

            # If event has no clear output field, stringify it
            if event:
                try:
                    return json.dumps(event, indent=2)
                except (TypeError, ValueError):
                    return str(event)

        return None

    def _score_text(self, text: str) -> int:
        """
        Score a text candidate based on heuristics.

        Args:
            text: The candidate text to score

        Returns:
            A score (higher is better). 0 means not relevant.
        """
        if not text or not isinstance(text, str):
            return 0

        score = 0

        # Check for "DONE" keyword (strong signal of completion)
        if 'DONE' in text.upper():
            score += self.score_weights['done_keyword']

        # Check for JSON structure (structured output is more reliable)
        if '{' in text and '}' in text:
            score += self.score_weights['json_structure']
            try:
                json.loads(text)
                score += 2  # Valid JSON bonus
            except json.JSONDecodeError:
                pass

        # Check for "status" field (indicates structured response)
        if '"status"' in text or "'status'" in text:
            score += self.score_weights['status_field']

        # Check for "result" field
        if '"result"' in text or "'result'" in text:
            score += self.score_weights['result_field']

        # Check for substantial length (avoid empty/trivial messages)
        if len(text) > 50:
            score += self.score_weights['substantial_length']

        return score


class PromptGenerator:
    """
    Generates context-aware prompts for Worker and Auditor agents.

    Injects the extracted result, feedback, and task metadata into prompts
    to provide continuity and context for multi-iteration loops.
    """

    def __init__(self, context):
        """
        Initialize the prompt generator.

        Args:
            context: ExecutionContext instance containing session data
        """
        self.context = context

    def generate_worker_prompt(
        self,
        task: str,
        iteration: int = 1,
        feedback: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a prompt for the Worker agent.

        Args:
            task: The original task description
            iteration: Current iteration number (1-based)
            feedback: Optional feedback from the Auditor for reiteration
            variables: Optional variable substitutions

        Returns:
            A formatted prompt for the Worker
        """
        prompt_parts = []

        # Task description
        prompt_parts.append(f"# Task (Iteration {iteration})\n")
        prompt_parts.append(task)
        prompt_parts.append("")

        # Feedback from previous iteration (if any)
        if feedback:
            prompt_parts.append("## Feedback from Auditor\n")
            prompt_parts.append(feedback)
            prompt_parts.append("")

        # Context from previous work
        if iteration > 1:
            worker_result = self.context.get_worker_result()
            if worker_result:
                prompt_parts.append("## Previous Work Summary\n")
                prompt_parts.append(worker_result)
                prompt_parts.append("")

        # Variable substitutions
        if variables:
            prompt_parts.append("## Variables\n")
            for key, value in variables.items():
                prompt_parts.append(f"- `{key}`: {value}")
            prompt_parts.append("")

        # Final instruction
        prompt_parts.append(
            "Please complete this task. When done, provide a summary "
            "of what was accomplished, starting with 'DONE'."
        )

        return "\n".join(prompt_parts)

    def generate_auditor_prompt(
        self,
        task: str,
        worker_result: str,
        iteration: int = 1,
    ) -> str:
        """
        Generate a prompt for the Auditor agent.

        Args:
            task: The original task description
            worker_result: The Worker's result/summary
            iteration: Current iteration number (1-based)

        Returns:
            A formatted prompt for the Auditor
        """
        prompt_parts = []

        prompt_parts.append("# Auditor Review\n")
        prompt_parts.append(f"Iteration: {iteration}\n")

        prompt_parts.append("## Original Task\n")
        prompt_parts.append(task)
        prompt_parts.append("")

        prompt_parts.append("## Worker's Result\n")
        prompt_parts.append(worker_result)
        prompt_parts.append("")

        prompt_parts.append(
            "## Your Assessment\n"
            "Review the worker's result and provide one of:\n"
            "1. DONE - if the task is complete and correct\n"
            "2. RETRY with feedback - if more work is needed\n"
            "3. IMPOSSIBLE - if the task cannot be completed\n\n"
            "Provide your verdict in JSON format with 'verdict' and 'feedback' fields."
        )

        return "\n".join(prompt_parts)

    def generate_recovery_prompt(
        self,
        task: str,
        last_state: str,
        executor_logs: Optional[str] = None,
    ) -> str:
        """
        Generate a prompt for recovery analysis.

        Args:
            task: The original task description
            last_state: The last recorded state before failure
            executor_logs: Optional logs from the executor for forensic analysis

        Returns:
            A formatted prompt for recovery analysis
        """
        prompt_parts = []

        prompt_parts.append("# Recovery Analysis\n")
        prompt_parts.append(f"Last State: {last_state}\n")

        prompt_parts.append("## Task Context\n")
        prompt_parts.append(task)
        prompt_parts.append("")

        if executor_logs:
            prompt_parts.append("## Executor Logs\n")
            prompt_parts.append(executor_logs)
            prompt_parts.append("")

        prompt_parts.append(
            "## Analysis Request\n"
            "Please determine if the task was completed despite the failure.\n"
            "Respond with JSON containing:\n"
            "- 'status': 'success', 'partial', or 'failed'\n"
            "- 'evidence': Description of findings\n"
            "- 'summary': Any recovered output"
        )

        return "\n".join(prompt_parts)
