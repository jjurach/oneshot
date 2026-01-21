"""
Protocol - Result Extraction and Prompt Generation

This module provides:
1. ResultExtractor: Parses activity logs and extracts the "best" result
2. PromptGenerator: Injects context into prompts for the Worker and Auditor
"""

import json
from typing import List, Tuple, Optional, Dict, Any
import re
from dataclasses import dataclass, field


@dataclass
class ResultSummary:
    """
    Summary of the best result and its context from activity logs.
    """
    result: str
    leading_context: List[str] = field(default_factory=list)
    trailing_context: List[str] = field(default_factory=list)
    score: int = 0

    def __bool__(self):
        return bool(self.result)


class ResultExtractor:
    """
    Extracts "Full Text" results from activity logs using fuzzy scoring and context capture.

    Processes noisy log streams and identifies high-quality output by
    scoring candidates based on heuristics (presence of "DONE", "STATUS", JSON structure, etc.).
    """

    def __init__(self):
        """Initialize the result extractor."""
        self.score_weights = {
            'done_keyword': 15,
            'status_keyword': 10,
            'success_keyword': 10,
            'json_structure': 5,
            'json_valid': 5,
            'substantial_length': 3,
            'status_field': 8,
            'result_field': 5,
            'human_keyword': -10,  # Penalty for human intervention requests
            'intervention_keyword': -10,
        }

    def extract_result(self, log_path: str) -> Optional[ResultSummary]:
        """
        Extract the best result from a log file with surrounding context.

        Args:
            log_path: Path to oneshot-log.json (NDJSON format)

        Returns:
            A ResultSummary object, or None if no valid content found
        """
        events = []
        try:
            with open(log_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        events.append(event)
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            return None
        except Exception:
            return None

        if not events:
            return None

        # Format events and score them
        scored_candidates = []
        for i, event in enumerate(events):
            text = self._format_event(event)
            if text:
                score = self._score_text(text)
                if score > 0:
                    scored_candidates.append((score, i, text))

        if not scored_candidates:
            # Fallback to last event if nothing scored high
            best_idx = len(events) - 1
            best_text = self._format_event(events[best_idx])
            best_score = 0
        else:
            # Sort by score (descending), then by index (latest first for ties)
            scored_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
            best_score, best_idx, best_text = scored_candidates[0]

        if not best_text:
            return None

        # Extract context (up to 2 leading, 2 trailing)
        leading_context = []
        for i in range(max(0, best_idx - 2), best_idx):
            ctx_text = self._format_event(events[i])
            if ctx_text:
                leading_context.append(ctx_text)

        trailing_context = []
        for i in range(best_idx + 1, min(len(events), best_idx + 3)):
            ctx_text = self._format_event(events[i])
            if ctx_text:
                trailing_context.append(ctx_text)

        return ResultSummary(
            result=best_text,
            leading_context=leading_context,
            trailing_context=trailing_context,
            score=best_score
        )

    def _format_event(self, event: Dict[str, Any]) -> Optional[str]:
        """
        Format an event object into a text representation.

        Args:
            event: A parsed JSON event from the log

        Returns:
            Formatted text, or None if the event is not useful
        """
        if not isinstance(event, dict):
            return str(event) if event else None

        # Check for common output fields from executors
        for field_name in ['output', 'stdout', 'text', 'content', 'message', 'data']:
            if field_name in event and event[field_name]:
                return str(event[field_name])

        # If it's a structured response (like a tool call or status update), stringify it
        if event:
            try:
                # Avoid dumping huge objects if possible, but for context we want full text
                return json.dumps(event)
            except (TypeError, ValueError):
                return str(event)

        return None

    def _score_text(self, text: str) -> int:
        """
        Score a text candidate based on fuzzy heuristics.

        Args:
            text: The candidate text to score

        Returns:
            A score (higher is better).
        """
        if not text:
            return 0

        score = 0
        text_upper = text.upper()

        # Keywords scoring
        if 'DONE' in text_upper:
            score += self.score_weights['done_keyword']
        if 'STATUS' in text_upper:
            score += self.score_weights['status_keyword']
        if 'SUCCESS' in text_upper:
            score += self.score_weights['success_keyword']
        
        # Requests for help/intervention (penalty)
        if 'HUMAN' in text_upper:
            score += self.score_weights['human_keyword']
        if 'INTERVENTION' in text_upper:
            score += self.score_weights['intervention_keyword']

        # JSON patterns
        if '{' in text and '}' in text:
            score += self.score_weights['json_structure']
            try:
                # Check for actual valid JSON
                # Some agents output JSON inside markdown, we try to find it
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    json.loads(json_match.group())
                    score += self.score_weights['json_valid']
            except:
                pass

        # Field-specific scoring (if text is JSON string)
        if '"status"' in text or "'status'" in text:
            score += self.score_weights['status_field']
        if '"result"' in text or "'result'" in text:
            score += self.score_weights['result_field']

        # Length bonus
        if len(text) > 100:
            score += self.score_weights['substantial_length']

        return score

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
    Generates context-aware XML-based prompts for Worker and Auditor agents.

    Injects the extracted result, feedback, and task metadata into prompts
    to provide continuity and context for multi-iteration loops.
    """

    def __init__(self, context=None, max_prompt_length: int = 100000):
        """
        Initialize the prompt generator.

        Args:
            context: Optional ExecutionContext instance containing session data
            max_prompt_length: Maximum allowed length for the prompt
        """
        self.context = context
        self.max_prompt_length = max_prompt_length

    def generate_worker_prompt(
        self,
        oneshot_id: str,
        iteration: int,
        instruction: str,
        system_prompt: str,
        auditor_feedback: Optional[str] = None,
        reworker_system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate a worker prompt using XML layout.
        """
        parts = []
        parts.append(f"<oneshot>{oneshot_id} worker #{iteration}</oneshot>\n")

        if auditor_feedback:
            parts.append("<auditor-feedback>")
            parts.append(auditor_feedback)
            parts.append("</auditor-feedback>\n")
            
            parts.append("<instruction>")
            parts.append(instruction)
            parts.append("</instruction>\n")
            
            if reworker_system_prompt:
                parts.append(reworker_system_prompt)
        else:
            parts.append(system_prompt)
            parts.append("\n")
            parts.append("<instruction>")
            parts.append(instruction)
            parts.append("</instruction>")

        prompt = "\n".join(parts)
        return self._truncate_to_limit(prompt)

    def generate_auditor_prompt(
        self,
        oneshot_id: str,
        iteration: int,
        original_prompt: str,
        result_summary: ResultSummary,
        auditor_system_prompt: str,
    ) -> str:
        """
        Generate an auditor prompt using XML layout.
        """
        parts = []
        parts.append(f"<oneshot>{oneshot_id} audit #{iteration}</oneshot>\n")

        parts.append("<what-was-requested>")
        parts.append(original_prompt)
        parts.append("</what-was-requested>\n")

        parts.append("<worker-result>")
        
        if result_summary.leading_context:
            parts.append(" <leading-context>")
            parts.append("\n".join(result_summary.leading_context))
            parts.append(" </leading-context>")
        
        parts.append(result_summary.result)
        
        if result_summary.trailing_context:
            parts.append(" <trailing-context>")
            parts.append("\n".join(result_summary.trailing_context))
            parts.append(" </trailing-context>")
            
        parts.append("</worker-result>\n")
        parts.append(auditor_system_prompt)

        prompt = "\n".join(parts)
        return self._truncate_to_limit(prompt)

    def _truncate_to_limit(self, prompt: str) -> str:
        """Truncate prompt if it exceeds max_prompt_length (simple character truncation)."""
        if len(prompt) > self.max_prompt_length:
            return prompt[:self.max_prompt_length] + "... [TRUNCATED]"
        return prompt
