"""
Oneshot Terminal User Interface (TUI)

Rich-based terminal dashboard for real-time monitoring and control of Oneshot tasks.
Provides interactive panels, keyboard shortcuts, and live updates.
"""

import asyncio
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.columns import Columns
from rich.align import Align
from rich.layout import Layout

from .events import event_emitter, EventType, EventPayload
from .orchestrator import AsyncOrchestrator


class TaskDisplay:
    """Display representation of a task."""

    def __init__(self, task_id: str, data: Dict[str, Any]):
        self.task_id = task_id
        self.state = data.get('state', 'unknown')
        self.command = data.get('command', '')
        self.start_time = data.get('timestamp', datetime.now().isoformat())
        self.exit_code = data.get('exit_code')
        self.execution_time = data.get('execution_time', 0)

    def get_state_style(self) -> str:
        """Get the color style for the current state."""
        styles = {
            'running': 'bold green',
            'idle': 'bold yellow',
            'completed': 'bold blue',
            'failed': 'bold red',
            'interrupted': 'bold orange',
            'created': 'dim white'
        }
        return styles.get(self.state, 'white')

    def to_table_row(self) -> List[str]:
        """Convert task to table row."""
        start_dt = datetime.fromisoformat(self.start_time.replace('Z', '+00:00'))
        start_str = start_dt.strftime('%H:%M:%S')

        exec_time = f"{self.execution_time:.1f}s" if self.execution_time else "-"
        exit_code = str(self.exit_code) if self.exit_code is not None else "-"

        return [
            self.task_id[:8] + "..." if len(self.task_id) > 8 else self.task_id,
            self.state,
            self.command[:30] + "..." if len(self.command) > 30 else self.command,
            start_str,
            exec_time,
            exit_code
        ]


class OneshotTUI:
    """
    Terminal User Interface for Oneshot task monitoring and control.

    Provides real-time display of tasks, system status, and keyboard controls
    for task interruption and navigation.
    """

    def __init__(self, orchestrator: Optional[AsyncOrchestrator] = None, refresh_rate: float = 1.0):
        """
        Initialize the TUI.

        Args:
            orchestrator: Optional orchestrator instance for task management
            refresh_rate: How often to refresh the display (seconds)
        """
        self.orchestrator = orchestrator
        self.refresh_rate = refresh_rate
        self.console = Console()
        self.tasks: Dict[str, TaskDisplay] = {}
        self.system_stats = {
            'total_tasks': 0,
            'running_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'interrupted_tasks': 0,
            'max_concurrent': 5
        }

        self.running = False
        self.selected_task_index = 0
        self.layout = Layout()

        # Event handling
        self._setup_event_handling()

    def _setup_event_handling(self):
        """Set up event handling for UI updates."""

        async def handle_task_event(event: EventPayload):
            """Handle task events and update display."""
            task_id = getattr(event, 'task_id', None)
            if task_id:
                task_data = getattr(event, 'data', {}) or {}
                task_data['timestamp'] = event.timestamp
                task_data['state'] = getattr(event, 'state', None) or task_data.get('state')

                self.tasks[task_id] = TaskDisplay(task_id, task_data)

        async def handle_system_event(event: EventPayload):
            """Handle system events and update stats."""
            if hasattr(event, 'total_tasks'):
                # SystemStatusPayload
                self.system_stats.update({
                    'total_tasks': event.total_tasks,
                    'running_tasks': event.running_tasks,
                    'completed_tasks': event.completed_tasks,
                    'failed_tasks': event.failed_tasks,
                    'interrupted_tasks': event.interrupted_tasks,
                    'max_concurrent': event.max_concurrent
                })

        # Subscribe to events
        asyncio.create_task(event_emitter.subscribe(EventType.TASK_CREATED, handle_task_event))
        asyncio.create_task(event_emitter.subscribe(EventType.TASK_STARTED, handle_task_event))
        asyncio.create_task(event_emitter.subscribe(EventType.TASK_IDLE, handle_task_event))
        asyncio.create_task(event_emitter.subscribe(EventType.TASK_ACTIVITY, handle_task_event))
        asyncio.create_task(event_emitter.subscribe(EventType.TASK_INTERRUPTED, handle_task_event))
        asyncio.create_task(event_emitter.subscribe(EventType.TASK_COMPLETED, handle_task_event))
        asyncio.create_task(event_emitter.subscribe(EventType.TASK_FAILED, handle_task_event))
        asyncio.create_task(event_emitter.subscribe(EventType.SYSTEM_STATUS, handle_system_event))

    def create_layout(self) -> Layout:
        """Create the main layout."""
        layout = Layout()

        # Split into header and main content
        layout.split(
            Layout(name="header", size=6),
            Layout(name="main")
        )

        # Split main into sidebar and content
        layout["main"].split_row(
            Layout(name="sidebar", ratio=1),
            Layout(name="content", ratio=3)
        )

        # Split content into task list and details
        layout["main"]["content"].split(
            Layout(name="task_list"),
            Layout(name="details", size=8)
        )

        return layout

    def create_header_panel(self) -> Panel:
        """Create the header panel with system stats."""
        stats = self.system_stats

        header_text = Text(justify="center")
        header_text.append("🎯 Oneshot Task Monitor", style="bold magenta")
        header_text.append(f"\nTotal: {stats['total_tasks']} | ", style="blue")
        header_text.append(f"Running: {stats['running_tasks']} | ", style="green")
        header_text.append(f"Completed: {stats['completed_tasks']} | ", style="blue")
        header_text.append(f"Failed: {stats['failed_tasks']} | ", style="red")
        header_text.append(f"Interrupted: {stats['interrupted_tasks']}", style="orange")

        return Panel(
            Align.center(header_text),
            title="[bold]System Status[/bold]",
            border_style="blue"
        )

    def create_task_table(self) -> Table:
        """Create the task table."""
        table = Table(title="Active Tasks", show_header=True, header_style="bold cyan")
        table.add_column("Task ID", style="dim", width=12)
        table.add_column("State", width=10)
        table.add_column("Command", width=32)
        table.add_column("Started", width=8)
        table.add_column("Time", width=8)
        table.add_column("Exit", width=4)

        # Sort tasks by start time (most recent first)
        sorted_tasks = sorted(
            self.tasks.values(),
            key=lambda t: t.start_time,
            reverse=True
        )

        for i, task in enumerate(sorted_tasks):
            row_style = "reverse" if i == self.selected_task_index else None
            table.add_row(*task.to_table_row(), style=row_style)

        if not self.tasks:
            table.add_row("[dim]No active tasks[/dim]", "", "", "", "", "")

        return table

    def create_task_details(self) -> Panel:
        """Create the task details panel."""
        if not self.tasks:
            return Panel(
                Align.center("[dim]No task selected[/dim]"),
                title="[bold]Task Details[/bold]"
            )

        # Get selected task
        sorted_tasks = sorted(
            self.tasks.values(),
            key=lambda t: t.start_time,
            reverse=True
        )

        if self.selected_task_index >= len(sorted_tasks):
            self.selected_task_index = 0

        if not sorted_tasks:
            return Panel(
                Align.center("[dim]No tasks available[/dim]"),
                title="[bold]Task Details[/bold]"
            )

        task = sorted_tasks[self.selected_task_index]

        details = Text()
        details.append(f"Task ID: {task.task_id}\n", style="bold")
        details.append(f"State: {task.state}\n", style=task.get_state_style())
        details.append(f"Command: {task.command}\n", style="cyan")
        details.append(f"Started: {task.start_time}\n", style="yellow")

        if task.execution_time:
            details.append(f"Execution Time: {task.execution_time:.2f}s\n", style="green")

        if task.exit_code is not None:
            exit_style = "green" if task.exit_code == 0 else "red"
            details.append(f"Exit Code: {task.exit_code}\n", style=exit_style)

        return Panel(
            details,
            title=f"[bold]Task Details[/bold]",
            border_style="green"
        )

    def create_sidebar(self) -> Panel:
        """Create the sidebar with controls."""
        controls = Text()
        controls.append("Controls:\n", style="bold")
        controls.append("↑/↓ - Navigate tasks\n", style="dim")
        controls.append("i - Interrupt selected task\n", style="dim")
        controls.append("r - Refresh display\n", style="dim")
        controls.append("q - Quit\n", style="dim")
        controls.append("\n")
        controls.append("Real-time updates active\n", style="green")
        controls.append(f"Refresh rate: {self.refresh_rate}s\n", style="blue")

        if self.orchestrator:
            controls.append(f"Max concurrent: {self.orchestrator.max_concurrent}\n", style="cyan")

        return Panel(
            controls,
            title="[bold]Controls[/bold]",
            border_style="yellow"
        )

    def create_display(self) -> Layout:
        """Create the complete display layout."""
        layout = self.create_layout()

        # Update layout sections
        layout["header"].update(self.create_header_panel())
        layout["main"]["sidebar"].update(self.create_sidebar())
        layout["main"]["content"]["task_list"].update(self.create_task_table())
        layout["main"]["content"]["details"].update(self.create_task_details())

        return layout

    def handle_keypress(self, key: str) -> bool:
        """
        Handle keyboard input.

        Args:
            key: The pressed key

        Returns:
            True if should continue, False to quit
        """
        if key == 'q':
            return False
        elif key == 'r':
            # Force refresh - handled by main loop
            pass
        elif key == 'i':
            self.interrupt_selected_task()
        elif key == '\x1b[A':  # Up arrow
            self.selected_task_index = max(0, self.selected_task_index - 1)
        elif key == '\x1b[B':  # Down arrow
            max_index = max(0, len(self.tasks) - 1)
            self.selected_task_index = min(max_index, self.selected_task_index + 1)

        return True

    def interrupt_selected_task(self):
        """Interrupt the currently selected task."""
        if not self.orchestrator or not self.tasks:
            return

        sorted_tasks = sorted(
            self.tasks.values(),
            key=lambda t: t.start_time,
            reverse=True
        )

        if self.selected_task_index < len(sorted_tasks):
            task = sorted_tasks[self.selected_task_index]
            if task.state in ['running', 'idle']:
                try:
                    self.orchestrator.interrupt_task(task.task_id)
                    self.console.print(f"[green]Interrupted task: {task.task_id}[/green]")
                except Exception as e:
                    self.console.print(f"[red]Failed to interrupt task: {e}[/red]")

    async def run_async(self):
        """Run the TUI asynchronously."""
        self.running = True

        def input_thread():
            """Handle keyboard input in a separate thread."""
            while self.running:
                try:
                    import sys
                    import tty
                    import termios

                    # Save terminal settings
                    old_settings = termios.tcgetattr(sys.stdin)

                    try:
                        tty.setcbreak(sys.stdin.fileno())

                        while self.running:
                            key = sys.stdin.read(1)
                            if key == '\x1b':  # Escape sequence
                                key += sys.stdin.read(2)  # Read the rest

                            # Handle the keypress in the main thread
                            if not self.handle_keypress(key):
                                self.running = False
                                break

                    finally:
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

                except (KeyboardInterrupt, EOFError):
                    self.running = False
                    break

        # Start input handling thread
        input_thread_handle = threading.Thread(target=input_thread, daemon=True)
        input_thread_handle.start()

        try:
            with Live(self.create_display(), refresh_per_second=1/self.refresh_rate, console=self.console) as live:
                while self.running:
                    # Update display
                    live.update(self.create_display())

                    # Small delay to prevent excessive CPU usage
                    await asyncio.sleep(self.refresh_rate)

        except KeyboardInterrupt:
            self.running = False

        # Wait for input thread to finish
        input_thread_handle.join(timeout=1.0)

    def run(self):
        """Run the TUI (blocking)."""
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            self.console.print("[yellow]TUI interrupted by user[/yellow]")

    async def cleanup(self):
        """Clean up resources."""
        self.running = False


# Convenience function to create and run TUI
def run_tui(orchestrator: Optional[AsyncOrchestrator] = None,
            refresh_rate: float = 1.0):
    """
    Create and run the Oneshot TUI.

    Args:
        orchestrator: Optional orchestrator instance
        refresh_rate: Display refresh rate in seconds
    """
    tui = OneshotTUI(orchestrator, refresh_rate)
    tui.run()


# Async version for integration with other async code
async def run_tui_async(orchestrator: Optional[AsyncOrchestrator] = None,
                       refresh_rate: float = 1.0):
    """
    Create and run the Oneshot TUI asynchronously.

    Args:
        orchestrator: Optional orchestrator instance
        refresh_rate: Display refresh rate in seconds
    """
    tui = OneshotTUI(orchestrator, refresh_rate)
    await tui.run_async()