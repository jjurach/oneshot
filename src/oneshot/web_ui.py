"""
Oneshot Web UI

FastAPI-based web dashboard for real-time monitoring and control of Oneshot tasks.
Provides REST API endpoints and WebSocket streaming for task management.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .events import event_emitter, EventType, EventPayload, emit_system_status
from .orchestrator import AsyncOrchestrator


class TaskInterruptRequest(BaseModel):
    """Request model for interrupting a task."""
    task_id: str


class SystemStatusResponse(BaseModel):
    """Response model for system status."""
    total_tasks: int
    running_tasks: int
    completed_tasks: int
    failed_tasks: int
    interrupted_tasks: int
    max_concurrent: int
    timestamp: str


class WebUIApp:
    """
    Web UI application for Oneshot task monitoring and control.
    """

    def __init__(self, orchestrator: Optional[AsyncOrchestrator] = None):
        """
        Initialize the web UI.

        Args:
            orchestrator: Optional orchestrator instance for task management
        """
        self.orchestrator = orchestrator
        self.app = FastAPI(title="Oneshot Dashboard", description="Real-time task monitoring and control")
        self.active_connections: List[WebSocket] = []

        # Static files not needed - dashboard HTML is embedded
        # self.app.mount("/static", StaticFiles(directory="static", html=True), name="static")

        # Set up routes
        self._setup_routes()

        # Event handling
        self._setup_event_handling()

    def _setup_routes(self):
        """Set up FastAPI routes."""

        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard():
            """Serve the main dashboard HTML page."""
            return self._get_dashboard_html()

        @self.app.get("/api/status")
        async def get_system_status() -> SystemStatusResponse:
            """Get current system status."""
            if not self.orchestrator:
                return SystemStatusResponse(
                    total_tasks=0,
                    running_tasks=0,
                    completed_tasks=0,
                    failed_tasks=0,
                    interrupted_tasks=0,
                    max_concurrent=5,
                    timestamp=datetime.now().isoformat()
                )

            stats = self.orchestrator.stats
            return SystemStatusResponse(
                total_tasks=stats['total_tasks'],
                running_tasks=stats['running'],
                completed_tasks=stats['completed'],
                failed_tasks=stats['failed'],
                interrupted_tasks=stats['interrupted'],
                max_concurrent=self.orchestrator.max_concurrent,
                timestamp=datetime.now().isoformat()
            )

        @self.app.post("/api/tasks/{task_id}/interrupt")
        async def interrupt_task(task_id: str, request: TaskInterruptRequest):
            """Interrupt a running task."""
            if not self.orchestrator:
                raise HTTPException(status_code=503, detail="Orchestrator not available")

            try:
                self.orchestrator.interrupt_task(task_id)
                return {"status": "success", "message": f"Task {task_id} interrupted"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to interrupt task: {str(e)}")

        @self.app.websocket("/ws/events")
        async def websocket_events(websocket: WebSocket):
            """WebSocket endpoint for real-time event streaming."""
            await websocket.accept()
            self.active_connections.append(websocket)

            try:
                # Send current system status on connection
                status = await get_system_status()
                await websocket.send_json({
                    "type": "system_status",
                    "data": status.dict()
                })

                # Keep connection alive and handle incoming messages
                while True:
                    try:
                        # Wait for messages with timeout
                        data = await asyncio.wait_for(
                            websocket.receive_json(),
                            timeout=30.0
                        )

                        # Handle incoming commands
                        await self._handle_websocket_command(websocket, data)

                    except asyncio.TimeoutError:
                        # Send ping to keep connection alive
                        await websocket.send_json({"type": "ping"})
                        continue

            except WebSocketDisconnect:
                pass
            finally:
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)

    def _setup_event_handling(self):
        """Set up event handling for broadcasting to WebSocket clients."""

        async def handle_task_event(event: EventPayload):
            """Handle task events and broadcast to WebSocket clients."""
            # Convert event to dict for JSON serialization
            event_data = event.to_dict()

            # Broadcast to all connected clients
            disconnected = []
            for websocket in self.active_connections:
                try:
                    await websocket.send_json({
                        "type": "task_event",
                        "data": event_data
                    })
                except Exception:
                    # Client disconnected
                    disconnected.append(websocket)

            # Clean up disconnected clients
            for websocket in disconnected:
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)

        async def handle_system_event(event: EventPayload):
            """Handle system events and broadcast to WebSocket clients."""
            event_data = event.to_dict()

            # Broadcast to all connected clients
            disconnected = []
            for websocket in self.active_connections:
                try:
                    await websocket.send_json({
                        "type": "system_event",
                        "data": event_data
                    })
                except Exception:
                    # Client disconnected
                    disconnected.append(websocket)

            # Clean up disconnected clients
            for websocket in disconnected:
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)

        # Subscribe to events
        asyncio.create_task(event_emitter.subscribe(EventType.TASK_CREATED, handle_task_event))
        asyncio.create_task(event_emitter.subscribe(EventType.TASK_STARTED, handle_task_event))
        asyncio.create_task(event_emitter.subscribe(EventType.TASK_IDLE, handle_task_event))
        asyncio.create_task(event_emitter.subscribe(EventType.TASK_ACTIVITY, handle_task_event))
        asyncio.create_task(event_emitter.subscribe(EventType.TASK_INTERRUPTED, handle_task_event))
        asyncio.create_task(event_emitter.subscribe(EventType.TASK_COMPLETED, handle_task_event))
        asyncio.create_task(event_emitter.subscribe(EventType.TASK_FAILED, handle_task_event))
        asyncio.create_task(event_emitter.subscribe(EventType.SYSTEM_STATUS, handle_system_event))

    async def _handle_websocket_command(self, websocket: WebSocket, data: Dict[str, Any]):
        """Handle incoming WebSocket commands."""
        command_type = data.get("type")

        if command_type == "interrupt_task":
            task_id = data.get("task_id")
            if task_id and self.orchestrator:
                try:
                    self.orchestrator.interrupt_task(task_id)
                    await websocket.send_json({
                        "type": "command_response",
                        "command": "interrupt_task",
                        "task_id": task_id,
                        "status": "success"
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "command_response",
                        "command": "interrupt_task",
                        "task_id": task_id,
                        "status": "error",
                        "message": str(e)
                    })

        elif command_type == "get_status":
            # Send current status
            status = await self.app.routes[1].endpoint()  # get_system_status endpoint
            await websocket.send_json({
                "type": "system_status",
                "data": status.dict()
            })

    def _get_dashboard_html(self) -> str:
        """Generate the dashboard HTML page."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Oneshot Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 min-h-screen">
    <div id="app" class="container mx-auto px-4 py-8">
        <header class="mb-8">
            <h1 class="text-3xl font-bold text-gray-800 mb-2">Oneshot Dashboard</h1>
            <div id="system-status" class="bg-white rounded-lg shadow p-4">
                <h2 class="text-xl font-semibold mb-4">System Status</h2>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div class="text-center">
                        <div class="text-2xl font-bold text-blue-600" id="total-tasks">0</div>
                        <div class="text-sm text-gray-600">Total Tasks</div>
                    </div>
                    <div class="text-center">
                        <div class="text-2xl font-bold text-green-600" id="running-tasks">0</div>
                        <div class="text-sm text-gray-600">Running</div>
                    </div>
                    <div class="text-center">
                        <div class="text-2xl font-bold text-purple-600" id="completed-tasks">0</div>
                        <div class="text-sm text-gray-600">Completed</div>
                    </div>
                    <div class="text-center">
                        <div class="text-2xl font-bold text-red-600" id="failed-tasks">0</div>
                        <div class="text-sm text-gray-600">Failed</div>
                    </div>
                </div>
            </div>
        </header>

        <main>
            <div class="bg-white rounded-lg shadow">
                <div class="p-4 border-b">
                    <h2 class="text-xl font-semibold">Task List</h2>
                </div>
                <div id="task-list" class="p-4">
                    <div class="text-center text-gray-500 py-8">
                        No tasks running. Start Oneshot with tasks to see them here.
                    </div>
                </div>
            </div>
        </main>
    </div>

    <script>
        class OneshotDashboard {
            constructor() {
                this.tasks = new Map();
                this.websocket = null;
                this.connectWebSocket();
                this.loadInitialStatus();
            }

            connectWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws/events`;

                this.websocket = new WebSocket(wsUrl);

                this.websocket.onopen = () => {
                    console.log('WebSocket connected');
                };

                this.websocket.onmessage = (event) => {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                };

                this.websocket.onclose = () => {
                    console.log('WebSocket disconnected, reconnecting...');
                    setTimeout(() => this.connectWebSocket(), 1000);
                };

                this.websocket.onerror = (error) => {
                    console.error('WebSocket error:', error);
                };
            }

            async loadInitialStatus() {
                try {
                    const response = await fetch('/api/status');
                    const status = await response.json();
                    this.updateSystemStatus(status);
                } catch (error) {
                    console.error('Failed to load initial status:', error);
                }
            }

            handleMessage(message) {
                switch (message.type) {
                    case 'task_event':
                        this.handleTaskEvent(message.data);
                        break;
                    case 'system_event':
                        if (message.data.event_type === 'system_status') {
                            this.updateSystemStatus(message.data);
                        }
                        break;
                    case 'system_status':
                        this.updateSystemStatus(message.data);
                        break;
                }
            }

            handleTaskEvent(eventData) {
                const taskId = eventData.task_id;
                const taskData = eventData.data || {};

                // Update or create task
                this.tasks.set(taskId, {
                    id: taskId,
                    state: eventData.state || taskData.state,
                    command: taskData.command,
                    startTime: eventData.timestamp,
                    exitCode: taskData.exit_code,
                    executionTime: taskData.execution_time
                });

                this.updateTaskList();
            }

            updateSystemStatus(status) {
                document.getElementById('total-tasks').textContent = status.total_tasks || 0;
                document.getElementById('running-tasks').textContent = status.running_tasks || 0;
                document.getElementById('completed-tasks').textContent = status.completed_tasks || 0;
                document.getElementById('failed-tasks').textContent = status.failed_tasks || 0;
            }

            updateTaskList() {
                const taskList = document.getElementById('task-list');
                const tasks = Array.from(this.tasks.values());

                if (tasks.length === 0) {
                    taskList.innerHTML = '<div class="text-center text-gray-500 py-8">No tasks running. Start Oneshot with tasks to see them here.</div>';
                    return;
                }

                const taskHtml = tasks.map(task => `
                    <div class="border rounded-lg p-4 mb-4">
                        <div class="flex justify-between items-start mb-2">
                            <div>
                                <h3 class="font-semibold text-lg">${task.id}</h3>
                                <p class="text-sm text-gray-600 font-mono">${task.command || 'No command'}</p>
                            </div>
                            <div class="flex items-center space-x-2">
                                <span class="px-2 py-1 rounded text-sm font-medium ${this.getStateColor(task.state)}">
                                    ${task.state || 'unknown'}
                                </span>
                                ${this.getActionButton(task)}
                            </div>
                        </div>
                        <div class="text-sm text-gray-500">
                            Started: ${new Date(task.startTime).toLocaleString()}
                            ${task.executionTime ? `<br>Execution time: ${task.executionTime.toFixed(2)}s` : ''}
                            ${task.exitCode !== null && task.exitCode !== undefined ? `<br>Exit code: ${task.exitCode}` : ''}
                        </div>
                    </div>
                `).join('');

                taskList.innerHTML = taskHtml;
            }

            getStateColor(state) {
                const colors = {
                    'running': 'bg-green-100 text-green-800',
                    'idle': 'bg-yellow-100 text-yellow-800',
                    'completed': 'bg-blue-100 text-blue-800',
                    'failed': 'bg-red-100 text-red-800',
                    'interrupted': 'bg-orange-100 text-orange-800',
                    'created': 'bg-gray-100 text-gray-800'
                };
                return colors[state] || 'bg-gray-100 text-gray-800';
            }

            getActionButton(task) {
                if (task.state === 'running' || task.state === 'idle') {
                    return `<button onclick="dashboard.interruptTask('${task.id}')"
                            class="px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600">
                        Interrupt
                    </button>`;
                }
                return '';
            }

            async interruptTask(taskId) {
                try {
                    const response = await fetch(`/api/tasks/${taskId}/interrupt`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ task_id: taskId })
                    });

                    if (response.ok) {
                        alert(`Task ${taskId} interrupted successfully`);
                    } else {
                        const error = await response.json();
                        alert(`Failed to interrupt task: ${error.detail}`);
                    }
                } catch (error) {
                    alert(`Error interrupting task: ${error.message}`);
                }
            }
        }

        // Initialize dashboard when page loads
        const dashboard = new OneshotDashboard();
    </script>
</body>
</html>
        """

    def get_app(self) -> FastAPI:
        """Get the FastAPI application instance."""
        return self.app

    async def start_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the web server."""
        import uvicorn
        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

    async def broadcast_system_status(self):
        """Broadcast current system status to all connected clients."""
        if self.orchestrator:
            stats = self.orchestrator.stats
            await emit_system_status(
                stats['total_tasks'],
                stats['running'],
                stats['completed'],
                stats['failed'],
                stats['interrupted'],
                self.orchestrator.max_concurrent
            )