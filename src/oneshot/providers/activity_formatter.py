"""
Activity Formatter for Terminal Display

Formats activity events from the activity interpreter into human-readable
terminal output with optional colorization and hierarchy.
"""

from typing import List, Optional
from .activity_interpreter import ActivityEvent, ActivityType


class ActivityFormatter:
    """Formats activity events for terminal/UI display."""

    # ANSI color codes
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'dim': '\033[2m',
        'blue': '\033[34m',
        'cyan': '\033[36m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'red': '\033[31m',
        'magenta': '\033[35m',
    }

    # Activity type to color mapping
    TYPE_COLORS = {
        ActivityType.TOOL_CALL: 'cyan',
        ActivityType.PLANNING: 'blue',
        ActivityType.REASONING: 'magenta',
        ActivityType.FILE_OPERATION: 'green',
        ActivityType.CODE_EXECUTION: 'yellow',
        ActivityType.API_CALL: 'cyan',
        ActivityType.THINKING: 'magenta',
        ActivityType.RESPONSE: 'green',
        ActivityType.ERROR: 'red',
        ActivityType.STATUS: 'dim',
    }

    # Activity type to icon mapping
    TYPE_ICONS = {
        ActivityType.TOOL_CALL: '🔧',
        ActivityType.PLANNING: '📋',
        ActivityType.REASONING: '🧠',
        ActivityType.FILE_OPERATION: '📄',
        ActivityType.CODE_EXECUTION: '⚙️',
        ActivityType.API_CALL: '🔌',
        ActivityType.THINKING: '💭',
        ActivityType.RESPONSE: '✅',
        ActivityType.ERROR: '❌',
        ActivityType.STATUS: 'ℹ️',
    }

    def __init__(self, use_colors: bool = True, use_icons: bool = False):
        """
        Initialize the formatter.

        Args:
            use_colors: Whether to use ANSI color codes
            use_icons: Whether to use unicode icons (requires terminal support)
        """
        self.use_colors = use_colors
        self.use_icons = use_icons

    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled."""
        if not self.use_colors:
            return text
        color_code = self.COLORS.get(color, '')
        reset_code = self.COLORS['reset']
        return f"{color_code}{text}{reset_code}"

    def _get_icon(self, activity_type: ActivityType) -> str:
        """Get icon for activity type if icons are enabled."""
        if not self.use_icons:
            return ''
        icon = self.TYPE_ICONS.get(activity_type, '•')
        return f"{icon} "

    def _get_color(self, activity_type: ActivityType) -> str:
        """Get color for activity type."""
        return self.TYPE_COLORS.get(activity_type, 'reset')

    def format_event(self, event: ActivityEvent, include_details: bool = False) -> str:
        """
        Format a single activity event for display.

        Args:
            event: The activity event to format
            include_details: Whether to include detailed information

        Returns:
            Formatted string suitable for terminal display
        """
        icon = self._get_icon(event.activity_type)
        color = self._get_color(event.activity_type)
        type_name = event.activity_type.value.upper()

        # Build the main line
        main = f"{icon}[{type_name}] {event.description}"
        formatted = self._colorize(main, color)

        # Add details if requested
        if include_details and event.details:
            details_lines = []
            for key, value in event.details.items():
                if isinstance(value, (str, int, float, bool)):
                    detail_line = f"  • {key}: {value}"
                    details_lines.append(self._colorize(detail_line, 'dim'))

            if details_lines:
                formatted = formatted + '\n' + '\n'.join(details_lines)

        return formatted

    def format_events(self, events: List[ActivityEvent], include_details: bool = False) -> str:
        """
        Format multiple activity events for display.

        Args:
            events: List of activity events to format
            include_details: Whether to include detailed information

        Returns:
            Formatted string with all events
        """
        if not events:
            return ""

        lines = []
        for event in events:
            lines.append(self.format_event(event, include_details))

        return '\n'.join(lines)

    def format_stream_update(self, event: ActivityEvent) -> str:
        """
        Format event for real-time streaming display (more compact).

        Args:
            event: The activity event to format

        Returns:
            Compact formatted string for streaming
        """
        icon = self._get_icon(event.activity_type)
        color = self._get_color(event.activity_type)

        # More compact format for streaming
        if event.activity_type == ActivityType.ERROR:
            line = f"{icon}ERROR: {event.description}"
        elif event.activity_type == ActivityType.PLANNING:
            line = f"{icon}{event.description}"
        else:
            line = f"{icon}{event.description}"

        return self._colorize(line, color)

    def format_activity_header(self, executor: str, task_id: Optional[str] = None) -> str:
        """
        Format a header for activity stream.

        Args:
            executor: Name of the executor
            task_id: Optional task ID

        Returns:
            Formatted header string
        """
        task_info = f" (task: {task_id})" if task_id else ""
        header = f"=== Activity Stream: {executor}{task_info} ==="
        return self._colorize(header, 'bold')

    def format_activity_footer(self, count: int) -> str:
        """
        Format a footer for activity stream.

        Args:
            count: Number of activities shown

        Returns:
            Formatted footer string
        """
        footer = f"=== {count} activity events ==="
        return self._colorize(footer, 'dim')

    def get_activity_summary(self, events: List[ActivityEvent]) -> str:
        """
        Get a summary of activities by type.

        Args:
            events: List of activity events

        Returns:
            Summary string with counts by type
        """
        counts = {}
        for event in events:
            activity_type = event.activity_type
            counts[activity_type] = counts.get(activity_type, 0) + 1

        if not counts:
            return "No activities recorded"

        summary_lines = ["Activity Summary:"]
        for activity_type in ActivityType:
            if activity_type in counts:
                count = counts[activity_type]
                line = f"  {self._get_icon(activity_type)}{activity_type.value}: {count}"
                summary_lines.append(line)

        return '\n'.join(summary_lines)


def format_for_display(events: List[ActivityEvent], executor: str = "executor",
                      task_id: Optional[str] = None, use_colors: bool = True) -> str:
    """
    Convenience function to format a list of activities for display.

    Args:
        events: List of activity events
        executor: Name of the executor
        task_id: Optional task ID
        use_colors: Whether to use colors

    Returns:
        Formatted display string
    """
    formatter = ActivityFormatter(use_colors=use_colors)

    lines = []
    lines.append(formatter.format_activity_header(executor, task_id))
    lines.append("")

    if events:
        lines.append(formatter.format_events(events, include_details=True))
        lines.append("")
        lines.append(formatter.format_activity_footer(len(events)))
    else:
        lines.append("No activity events recorded")

    return '\n'.join(lines)
