"""
Activity Interpreter for Claude Executor Output

Parses Claude executor streaming output and extracts meaningful activity
information while filtering sensitive metadata (costs, tokens, usage stats).
Converts raw output into structured activity events suitable for UI display.
"""

import json
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class ActivityType(Enum):
    """Types of meaningful Claude activity to track."""
    TOOL_CALL = "tool_call"
    PLANNING = "planning"
    REASONING = "reasoning"
    FILE_OPERATION = "file_operation"
    CODE_EXECUTION = "code_execution"
    API_CALL = "api_call"
    THINKING = "thinking"
    RESPONSE = "response"
    ERROR = "error"
    STATUS = "status"


@dataclass
class ActivityEvent:
    """Structured activity event extracted from executor output."""
    activity_type: ActivityType
    description: str
    details: Optional[Dict[str, Any]] = None
    is_sensitive: bool = False  # Whether this event contains sensitive info


class ActivityInterpreter:
    """
    Interprets Claude executor output and extracts meaningful activity patterns.

    Filters out:
    - Token counts and costs
    - API usage metrics
    - Internal usage statistics
    - Billing information

    Extracts and highlights:
    - Tool calls and actions
    - Planning and reasoning
    - File modifications
    - Command execution
    - Thinking steps
    """

    # Patterns for sensitive metadata to filter
    SENSITIVE_PATTERNS = [
        # Token and cost info
        r'(?:input|output|total)_tokens:\s*\d+',
        r'cache_creation_input_tokens:\s*\d+',
        r'cache_read_input_tokens:\s*\d+',
        r'tokens\s+used:\s*\d+',
        r'cost:\s*\$[\d.]+',
        r'input_cost:\s*\$[\d.]+',
        r'output_cost:\s*\$[\d.]+',
        r'total_cost:\s*\$[\d.]+',
        # Usage metrics
        r'usage:\s*{[^}]*}',
        r'rate[_-]limit(?:s)?:.*',
        # Billing-related
        r'billing_info.*',
        r'model_usage.*',
    ]

    # Tool call patterns
    TOOL_CALL_PATTERNS = [
        r'(?:Calling|Running|Executing|Invoking)\s+(?:tool|function|command):\s*([^\n]+)',
        r'<\s*(?:tool|function|command)\s+(?:call|use)\s*>\s*([^\n]+)',
        r'Tool:\s*([^\n]+)',
        r'bash\s+[\'"]([^\'"]+)[\'"]',
        r'python\s+(?:[\'"]([^\'"]+)[\'"]|([^\s]+))',
        r'(?:Running|Executing)\s+(?:python|bash)\s+(.+)',
    ]

    # Planning/thinking patterns
    PLANNING_PATTERNS = [
        r'(?:I think|I need to|Let me|I\'ll|First|Next|Then|My plan)',
        r'(?:Plan|Strategy|Approach):\s*([^\n]+)',
        r'(?:<thinking>|<think>)(.*?)(?:</thinking>|</think>)',
    ]

    # File operation patterns
    FILE_OPERATION_PATTERNS = [
        r'(?:Creating|Writing|Modifying|Editing|Reading|Deleting)\s+(?:file|path)\s*:?\s*([^\n\s]+)',
        r'file:\s*([^\n\s]+)',
        r'path:\s*([^\n\s]+)',
        r'(?:Created|Modified|Deleted|Wrote)\s+(?:file|path)\s*:?\s*([^\n\s]+)',
    ]

    # Error patterns
    ERROR_PATTERNS = [
        r'(?:Error|ERROR|Exception):\s*([^\n]+)',
        r'(?:Failed|FAILED)\s+(?:to|with):\s*([^\n]+)',
        r'(?:error:|Error occurred:)\s*([^\n]+)',
    ]

    def __init__(self):
        """Initialize the activity interpreter."""
        self.compiled_sensitive = [re.compile(p, re.IGNORECASE | re.MULTILINE)
                                   for p in self.SENSITIVE_PATTERNS]
        self.compiled_tools = [re.compile(p, re.IGNORECASE) for p in self.TOOL_CALL_PATTERNS]
        self.compiled_planning = [re.compile(p, re.IGNORECASE) for p in self.PLANNING_PATTERNS]
        self.compiled_files = [re.compile(p, re.IGNORECASE) for p in self.FILE_OPERATION_PATTERNS]
        self.compiled_errors = [re.compile(p, re.IGNORECASE) for p in self.ERROR_PATTERNS]

    def filter_metadata(self, text: str) -> str:
        """
        Remove cost, token, and usage metadata from text.

        Args:
            text: Raw output text

        Returns:
            Filtered text with sensitive metadata removed
        """
        filtered = text
        for pattern in self.compiled_sensitive:
            filtered = pattern.sub('', filtered)

        # Clean up leftover underscores and multiple consecutive newlines
        filtered = re.sub(r'\n_*\n', '\n', filtered)  # Remove lines with just underscores
        filtered = re.sub(r'_+\n', '\n', filtered)     # Remove underscores at end of lines
        filtered = re.sub(r'\n{3,}', '\n\n', filtered)

        return filtered.strip()

    def extract_tool_calls(self, text: str) -> List[ActivityEvent]:
        """
        Extract tool call activities from text.

        Args:
            text: Text to search

        Returns:
            List of tool call activity events
        """
        events = []

        for pattern in self.compiled_tools:
            matches = pattern.finditer(text)
            for match in matches:
                # Try to get the first non-None group
                tool_desc = None
                for group_idx in range(1, match.lastindex + 1 if match.lastindex else 1):
                    if match.group(group_idx):
                        tool_desc = match.group(group_idx)
                        break

                if not tool_desc:
                    tool_desc = match.group(0)

                events.append(ActivityEvent(
                    activity_type=ActivityType.TOOL_CALL,
                    description=f"Tool call: {tool_desc.strip()}",
                    details={"tool_description": tool_desc.strip()}
                ))

        return events

    def extract_file_operations(self, text: str) -> List[ActivityEvent]:
        """
        Extract file operation activities from text.

        Args:
            text: Text to search

        Returns:
            List of file operation activity events
        """
        events = []

        for pattern in self.compiled_files:
            matches = pattern.finditer(text)
            for match in matches:
                file_path = match.group(1) if match.lastindex >= 1 else match.group(0)
                events.append(ActivityEvent(
                    activity_type=ActivityType.FILE_OPERATION,
                    description=f"File operation: {file_path.strip()}",
                    details={"file_path": file_path.strip()}
                ))

        return events

    def extract_errors(self, text: str) -> List[ActivityEvent]:
        """
        Extract error activities from text.

        Args:
            text: Text to search

        Returns:
            List of error activity events
        """
        events = []

        for pattern in self.compiled_errors:
            matches = pattern.finditer(text)
            for match in matches:
                error_msg = match.group(1) if match.lastindex >= 1 else match.group(0)
                events.append(ActivityEvent(
                    activity_type=ActivityType.ERROR,
                    description=f"Error: {error_msg.strip()}",
                    details={"error_message": error_msg.strip()},
                    is_sensitive=True
                ))

        return events

    def extract_planning(self, text: str) -> List[ActivityEvent]:
        """
        Extract planning/thinking activities from text.

        Args:
            text: Text to search

        Returns:
            List of planning activity events
        """
        events = []

        # Look for thinking tags
        thinking_pattern = re.compile(r'(?:<thinking>|<think>)(.*?)(?:</thinking>|</think>)',
                                     re.IGNORECASE | re.DOTALL)
        for match in thinking_pattern.finditer(text):
            thinking_content = match.group(1).strip()
            # Only add if thinking content is substantial
            if len(thinking_content) > 10:
                summary = thinking_content[:100] + "..." if len(thinking_content) > 100 else thinking_content
                events.append(ActivityEvent(
                    activity_type=ActivityType.THINKING,
                    description=f"Thinking: {summary}",
                    details={"thinking_content": thinking_content}
                ))

        # Look for planning statements
        for pattern in self.compiled_planning:
            if pattern.search(text):
                # Extract first few planning lines
                lines = text.split('\n')
                for line in lines:
                    if pattern.search(line) and len(line) > 3:
                        summary = line[:100] + "..." if len(line) > 100 else line
                        events.append(ActivityEvent(
                            activity_type=ActivityType.PLANNING,
                            description=f"Planning: {summary.strip()}",
                            details={"planning_line": line.strip()}
                        ))
                        break

        return events

    def interpret_activity(self, raw_output: str, activity_logger=None) -> List[ActivityEvent]:
        """
        Interpret executor output and extract meaningful activity patterns.

        Args:
            raw_output: Raw output from Claude executor
            activity_logger: Optional ActivityLogger to log raw JSON activities

        Returns:
            List of structured activity events
        """
        events = []

        # Parse streaming JSON to extract raw activities for logging
        json_objects = []
        if activity_logger:
            try:
                # Try to parse raw_output as streaming JSON
                lines = raw_output.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        obj = json.loads(line)
                        json_objects.append(obj)
                        # Log each valid JSON object to NDJSON file
                        activity_logger.log_json_line(line)
                    except json.JSONDecodeError:
                        # Continue to next line, don't log malformed JSON
                        pass
            except Exception as e:
                # If JSON parsing fails completely, skip logging for this output
                pass

        # Filter metadata first to get clean output for analysis
        filtered = self.filter_metadata(raw_output)

        # Extract different types of activities
        events.extend(self.extract_errors(raw_output))  # Use raw for errors to preserve context
        events.extend(self.extract_tool_calls(filtered))
        events.extend(self.extract_file_operations(filtered))
        events.extend(self.extract_planning(filtered))

        # If no specific activities extracted, create a generic status event
        if not events and filtered:
            events.append(ActivityEvent(
                activity_type=ActivityType.STATUS,
                description="Processing output",
                details={"output_preview": filtered[:200]}
            ))

        return events

    def has_sensitive_data(self, text: str) -> bool:
        """
        Check if text contains sensitive metadata.

        Args:
            text: Text to check

        Returns:
            True if sensitive data is found
        """
        for pattern in self.compiled_sensitive:
            if pattern.search(text):
                return True
        return False

    def get_filtered_output(self, raw_output: str) -> str:
        """
        Get output with all sensitive metadata removed (for display).

        Args:
            raw_output: Raw executor output

        Returns:
            Filtered output safe to display to user
        """
        return self.filter_metadata(raw_output)


# Global instance for convenience
_interpreter = None

def get_interpreter() -> ActivityInterpreter:
    """Get or create the global activity interpreter instance."""
    global _interpreter
    if _interpreter is None:
        _interpreter = ActivityInterpreter()
    return _interpreter