#!/usr/bin/env python3
"""
Demo script to format sample-cline-activity.json into pretty human-readable output.

This script demonstrates the activity interpretation and formatting pipeline:
1. Reads NDJSON activity data from sample-cline-activity.json
2. Extracts meaningful activities using ActivityInterpreter
3. Formats them for display using ActivityFormatter
4. Shows both the raw filtered output and the structured activity events
"""

import json
import sys
import os
from pathlib import Path

# Add the src directory to Python path to import the activity modules
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from oneshot.providers.activity_interpreter import get_interpreter, ActivityInterpreter
from oneshot.providers.activity_formatter import ActivityFormatter, format_for_display


def read_ndjson_file(file_path: str) -> str:
    """Read NDJSON file and return concatenated JSON objects."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Filter out empty lines and join with newlines
        json_lines = [line.strip() for line in lines if line.strip()]
        return '\n'.join(json_lines)

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}")
        sys.exit(1)


def truncate_text(text: str, max_length: int = 1000, summary_length: int = 1500) -> str:
    """Truncate text intelligently, keeping meaningful content."""
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    # For very long text, take beginning and end with ellipsis
    start_len = max_length // 3
    end_len = max_length - start_len - 3  # -3 for "..."

    return text[:start_len] + "..." + text[-end_len:]


def summarize_json_object(obj: dict) -> str:
    """Create a human-readable summary of a JSON activity object."""
    obj_type = obj.get('type', 'unknown')
    obj_text = obj.get('text', '')
    timestamp = obj.get('ts', 0)
    say_type = obj.get('say', obj.get('ask', ''))

    # Convert timestamp to readable time
    import datetime
    try:
        dt = datetime.datetime.fromtimestamp(timestamp / 1000)
        time_str = dt.strftime('%H:%M:%S')
    except:
        time_str = f"ts:{timestamp}"

    if obj_type == 'say':
        if say_type == 'text':
            # Regular text output
            if obj_text.strip():
                summary = truncate_text(obj_text.strip())
                return f"[{time_str}] 💬 Said: {summary}"
            else:
                return f"[{time_str}] 💬 Said: (empty text)"

        elif say_type == 'reasoning':
            summary = truncate_text(obj_text.strip(), 500)  # Shorter for reasoning
            return f"[{time_str}] 🧠 Reasoning: {summary}"

        elif say_type == 'completion_result':
            summary = truncate_text(obj_text.strip(), 300)
            return f"[{time_str}] ✅ Result: {summary}"

        elif say_type == 'checkpoint_created':
            return f"[{time_str}] 📍 Checkpoint created"

        elif say_type == 'api_req_started':
            # Extract cost/token info if present
            tokens_in = obj.get('tokensIn', 0)
            tokens_out = obj.get('tokensOut', 0)
            cost = obj.get('cost', 0)
            return f"[{time_str}] 🔌 API Request: {tokens_in}→{tokens_out} tokens (${cost})"

        else:
            summary = truncate_text(obj_text.strip())
            return f"[{time_str}] 💬 Say ({say_type}): {summary}"

    elif obj_type == 'ask':
        if obj_text.strip():
            # Try to extract JSON response if present
            try:
                # Look for JSON in the text
                text_content = obj_text.strip()
                if text_content.startswith('{'):
                    json_data = json.loads(text_content)
                    status = json_data.get('status', json_data.get('verdict', 'unknown'))
                    result = json_data.get('result', json_data.get('reason', ''))
                    if result:
                        summary = truncate_text(result, 400)
                        return f"[{time_str}] ❓ Response ({status}): {summary}"
                    else:
                        return f"[{time_str}] ❓ Response: {status}"
                else:
                    summary = truncate_text(text_content)
                    return f"[{time_str}] ❓ Asked: {summary}"
            except:
                summary = truncate_text(obj_text.strip())
                return f"[{time_str}] ❓ Asked: {summary}"
        else:
            return f"[{time_str}] ❓ Ask: (empty)"

    else:
        # Unknown type
        summary = truncate_text(str(obj))
        return f"[{time_str}] ❓ {obj_type}: {summary}"


def main():
    """Main demo function."""
    # Path to sample activity file
    sample_file = "sample-cline-activity.json"

    print("=== Activity Formatting Demo ===\n")

    # Check if sample file exists
    if not os.path.exists(sample_file):
        print(f"Error: Sample file '{sample_file}' not found in current directory.")
        print(f"Current directory: {os.getcwd()}")
        sys.exit(1)

    # Read the NDJSON content
    print(f"Reading activity data from: {sample_file}")
    raw_content = read_ndjson_file(sample_file)
    print(f"Read {len(raw_content)} characters of raw activity data\n")

    # Parse all JSON objects
    print("=== ACTIVITY TIMELINE (Pretty Formatted) ===")
    lines = raw_content.split('\n')
    activity_count = 0
    total_objects = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        total_objects += 1
        try:
            obj = json.loads(line)
            summary = summarize_json_object(obj)

            # Only show activities that have meaningful content
            if len(summary) > 20:  # More than just timestamp and icon
                print(summary)
                activity_count += 1

                # Limit display to avoid overwhelming output
                if activity_count >= 20:
                    remaining = sum(1 for l in lines[total_objects:] if l.strip())
                    if remaining > 0:
                        print(f"... and {remaining} more activities")
                    break

        except json.JSONDecodeError:
            print(f"[ERROR] Malformed JSON: {line[:100]}...")
            continue

    print(f"\nDisplayed {activity_count} meaningful activities out of {total_objects} total JSON objects\n")

    # Initialize interpreter and formatter
    interpreter = get_interpreter()
    formatter = ActivityFormatter(use_colors=True, use_icons=True)

    # Extract activities using the existing pipeline
    print("=== STRUCTURED ACTIVITY ANALYSIS ===")
    activities = interpreter.interpret_activity(raw_content)

    if activities:
        # Group activities by type for better display
        activity_counts = {}
        for activity in activities:
            activity_type = activity.activity_type.value
            activity_counts[activity_type] = activity_counts.get(activity_type, 0) + 1

        print(f"🤖 AI Activity Summary: {len(activities)} events detected")
        for activity_type, count in activity_counts.items():
            activity_icon = {
                'tool_call': '🔧',
                'planning': '📋',
                'reasoning': '🧠',
                'file_operation': '📄',
                'code_execution': '⚙️',
                'api_call': '🔌',
                'thinking': '💭',
                'response': '✅',
                'error': '❌',
                'status': 'ℹ️'
            }.get(activity_type, '•')
            print(f"  {activity_icon} {activity_type.replace('_', ' ').title()}: {count}")
        print()

        # Display formatted activities
        formatted_display = format_for_display(
            activities,
            executor="cline",
            task_id="demo-task",
            use_colors=True
        )
        print("🎨 Formatted Activity Stream:")
        print(formatted_display)
    else:
        print("🤔 No structured activities extracted from the data.")
        print("\nThis could mean:")
        print("  • The JSON format doesn't match expected patterns")
        print("  • The content is primarily metadata that was filtered out")
        print("  • The activity interpreter needs updated patterns")

    print("\n=== SENSITIVE DATA FILTERING DEMO ===")
    filtered_output = interpreter.get_filtered_output(raw_content)
    original_tokens = len(raw_content.split())
    filtered_tokens = len(filtered_output.split()) if filtered_output else 0
    reduction = ((original_tokens - filtered_tokens) / original_tokens * 100) if original_tokens > 0 else 0

    print(f"📊 Filtering Results:")
    print(".1f")
    print(f"  • Sensitive metadata automatically removed")
    print(f"  • Cost information, token counts, and billing data hidden")
    print(f"  • Meaningful content preserved for user experience")

    print("\n=== Demo Complete ===")
    print("💡 This demonstrates how oneshot processes AI activity streams to provide")
    print("   clean, meaningful feedback to users while protecting sensitive information.")


if __name__ == "__main__":
    main()