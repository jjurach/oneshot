#!/usr/bin/env python3
"""
Oneshot-Cline Real-time Activity Integration

This module enables oneshot to monitor Cline activity with sub-second frequency
by monitoring the api_conversation_history.json file instead of CLI output.
"""

import os
import time
import threading
import queue
import json
import glob
import signal
import sys
from typing import Optional, Callable, List, Dict, Any, Tuple
from pathlib import Path
import select
import fcntl


class ClineConversationMonitor:
    """
    Monitors Cline activity in real-time by watching the conversation history file.

    This approach monitors the actual conversation data that Cline writes to disk,
    providing true real-time updates instead of static CLI output.
    """

    def __init__(self, activity_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.activity_callback = activity_callback
        self.monitoring = False
        self.activity_queue: queue.Queue = queue.Queue()
        self.monitor_thread: Optional[threading.Thread] = None
        self.process: Optional[subprocess.Popen] = None
        self.current_task_id: Optional[str] = None
        self.last_position = 0
        self.last_mtime = 0
        self.conversation_cache: List[Dict[str, Any]] = []

    def start_monitoring(self) -> None:
        """Start real-time monitoring of Cline conversation history."""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_conversation_history)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

    def get_latest_activities(self, max_activities: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent activity data."""
        activities = []
        try:
            while len(activities) < max_activities and not self.activity_queue.empty():
                activities.append(self.activity_queue.get_nowait())
        except queue.Empty:
            pass
        return activities

    def _find_active_task_directory(self) -> Optional[Tuple[str, Path]]:
        """Find the most recently active task directory."""
        try:
            tasks_dir = Path.home() / ".cline" / "data" / "tasks"
            if not tasks_dir.exists():
                return None

            # Get all task directories and sort by modification time (most recent first)
            task_dirs = []
            for task_dir in tasks_dir.iterdir():
                if task_dir.is_dir():
                    try:
                        # Check if it has the required files
                        conv_file = task_dir / "api_conversation_history.json"
                        if conv_file.exists():
                            mtime = conv_file.stat().st_mtime
                            task_dirs.append((task_dir.name, task_dir, mtime))
                    except (OSError, PermissionError):
                        continue

            if not task_dirs:
                return None

            # Sort by modification time (most recent first)
            task_dirs.sort(key=lambda x: x[2], reverse=True)
            task_id, task_dir, _ = task_dirs[0]

            return task_id, task_dir

        except (OSError, PermissionError) as e:
            print(f"Error finding task directory: {e}")
            return None

    def _monitor_conversation_history(self) -> None:
        """Monitor the conversation history file for changes."""
        while self.monitoring:
            try:
                # Find the active task directory
                result = self._find_active_task_directory()
                if not result:
                    time.sleep(1)  # Wait before retrying
                    continue

                task_id, task_dir = result
                conv_file = task_dir / "api_conversation_history.json"

                # Check if task changed
                if task_id != self.current_task_id:
                    print(f"Switched to monitoring task: {task_id}")
                    self.current_task_id = task_id
                    self.last_position = 0
                    self.last_mtime = 0
                    self.conversation_cache = []

                # Check if file exists and is readable
                if not conv_file.exists():
                    time.sleep(1)
                    continue

                # Check modification time
                try:
                    stat = conv_file.stat()
                    current_mtime = stat.st_mtime
                    current_size = stat.st_size
                except (OSError, PermissionError):
                    time.sleep(1)
                    continue

                # If file was modified or truncated
                if current_mtime != self.last_mtime or current_size < self.last_position:
                    self.last_position = 0  # Reset position if file changed
                    self.conversation_cache = []

                self.last_mtime = current_mtime

                # Read new content
                try:
                    with open(conv_file, 'r', encoding='utf-8') as f:
                        # Try to seek to last position
                        if self.last_position > 0:
                            try:
                                f.seek(self.last_position)
                            except (OSError, IOError):
                                # File was truncated or seek failed
                                f.seek(0)
                                self.last_position = 0
                                self.conversation_cache = []

                        content = f.read()
                        if content:
                            self.last_position = f.tell()
                            self._process_new_content(content)

                except (OSError, PermissionError, UnicodeDecodeError) as e:
                    print(f"Error reading conversation file: {e}")
                    time.sleep(1)
                    continue

            except Exception as e:
                print(f"Error in conversation monitoring: {e}")
                time.sleep(1)

            # Poll every 0.1 seconds for near real-time updates
            time.sleep(0.1)

    def _process_new_content(self, content: str) -> None:
        """Process new content from the conversation file."""
        try:
            # Find JSON array start/end
            content = content.strip()
            if not content.startswith('['):
                return

            # Parse the JSON array
            conversations = json.loads(content)

            # Check for new conversations
            new_conversations = []
            if len(conversations) > len(self.conversation_cache):
                new_conversations = conversations[len(self.conversation_cache):]
                self.conversation_cache = conversations
            elif len(conversations) == len(self.conversation_cache):
                # Check if the last conversation changed
                if conversations and self.conversation_cache and conversations[-1] != self.conversation_cache[-1]:
                    new_conversations = [conversations[-1]]
                    self.conversation_cache = conversations

            # Process new conversations
            for conversation in new_conversations:
                activities = self._parse_conversation(conversation)
                for activity in activities:
                    self.activity_queue.put(activity)
                    if self.activity_callback:
                        self.activity_callback(activity)

        except (json.JSONDecodeError, IndexError, TypeError) as e:
            # File might be partially written, skip this read
            pass

    def _parse_conversation(self, conversation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse a conversation entry into activity data."""
        activities = []
        timestamp = time.time()

        try:
            role = conversation.get('role', 'unknown')
            content = conversation.get('content', [])

            # Handle different content formats
            if isinstance(content, list):
                # New format with content array
                text_content = []
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        text_content.append(item['text'])
                    elif isinstance(item, str):
                        text_content.append(item)
                message_text = ' '.join(text_content)
            else:
                # Old format with direct content
                message_text = str(content)

            # Categorize activity types
            activity_type = 'unknown'
            if role == 'assistant':
                if 'thinking' in message_text.lower():
                    activity_type = 'thinking'
                elif any(keyword in message_text.lower() for keyword in ['tool', 'function', 'api', 'execute']):
                    activity_type = 'tool_usage'
                else:
                    activity_type = 'response'
            elif role == 'user':
                activity_type = 'user_input'

            # Extract additional metadata
            metadata = conversation.get('modelInfo', {})
            model_id = metadata.get('modelId', 'unknown')
            provider = metadata.get('providerId', 'unknown')

            activity = {
                'timestamp': timestamp,
                'type': activity_type,
                'role': role,
                'message': message_text[:200] + '...' if len(message_text) > 200 else message_text,
                'model': model_id,
                'provider': provider,
                'full_content': message_text,
                'raw_data': conversation
            }

            activities.append(activity)

        except Exception as e:
            # Create error activity for parsing failures
            activities.append({
                'timestamp': timestamp,
                'type': 'error',
                'message': f'Failed to parse conversation: {str(e)}',
                'raw_data': conversation
            })

        return activities


class OneshotClineIntegration:
    """
    Integration layer for oneshot to monitor Cline activity in real-time.
    """

    def __init__(self):
        self.monitor = ClineConversationMonitor(activity_callback=self._on_activity)
        self.activities: List[Dict[str, Any]] = []
        self.last_activity_time = 0

    def start_realtime_monitoring(self) -> None:
        """Start real-time monitoring of Cline activity."""
        print("Starting oneshot-cline real-time integration (file-based monitoring)...")
        print("Monitoring conversation history for real-time updates...")
        self.monitor.start_monitoring()

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        print("Stopping oneshot-cline integration...")
        self.monitor.stop_monitoring()

    def _on_activity(self, activity: Dict[str, Any]) -> None:
        """Handle new activity data."""
        self.activities.append(activity)
        self.last_activity_time = activity['timestamp']

        # Keep only recent activities (last 100)
        if len(self.activities) > 100:
            self.activities = self.activities[-100:]

        # Print activity for oneshot visibility
        print(f"[ONESHOT] Cline Activity: {activity['type']} - {activity['message']}")

    def get_recent_activity_summary(self, since_timestamp: float = 0) -> Dict[str, Any]:
        """Get summary of recent activity."""
        recent = [a for a in self.activities if a['timestamp'] > since_timestamp]

        return {
            'total_activities': len(recent),
            'time_range': f"{since_timestamp:.1f} - {time.time():.1f}",
            'activity_types': list(set(a['type'] for a in recent)),
            'latest_activity': recent[-1] if recent else None,
            'activities_per_second': len(recent) / max(1, time.time() - since_timestamp)
        }

    def wait_for_activity(self, timeout: float = 30.0, activity_type: str = None) -> Optional[Dict[str, Any]]:
        """Wait for specific activity type or any activity."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            recent = self.monitor.get_latest_activities(1)
            if recent:
                activity = recent[0]
                if activity_type is None or activity['type'] == activity_type:
                    return activity
            time.sleep(0.1)

        return None


def main():
    """Main function for testing the integration."""
    print("Oneshot-Cline Real-time Activity Monitor (File-based)")
    print("=" * 60)

    integration = OneshotClineIntegration()

    def signal_handler(signum, frame):
        print("\nShutting down...")
        integration.stop_monitoring()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        integration.start_realtime_monitoring()

        print("Monitoring Cline conversation history... Press Ctrl+C to stop")
        print("Activity will appear instantly when Cline processes messages!")

        while True:
            time.sleep(5)  # Check every 5 seconds for summary
            summary = integration.get_recent_activity_summary(time.time() - 10)
            if summary['total_activities'] > 0:
                print(f"Last 10s: {summary['total_activities']} activities "
                      f"({summary['activities_per_second']:.2f}/sec)")

    except KeyboardInterrupt:
        integration.stop_monitoring()


if __name__ == '__main__':
    main()