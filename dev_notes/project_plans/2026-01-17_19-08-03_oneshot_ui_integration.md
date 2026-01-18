# Project Plan: Oneshot UI Integration

**Status: IMPLEMENTED**

## Objective
Implement a user interface layer that exposes the asynchronous state machine transitions through an event-driven architecture. This will enable real-time monitoring and control of running tasks via web dashboards and terminal user interfaces, allowing users to visualize task states, interrupt processes, and monitor system health.

## Implementation Steps

1. **Design Event System Architecture** (Completed)
   - Create an `AsyncEventEmitter` class using `asyncio.Queue` for broadcasting state transitions
   - Define event types: `task_created`, `task_started`, `task_idle`, `task_interrupted`, `task_completed`, `task_failed`
   - Implement event payload structure with task metadata (ID, command, timestamps, current state)

2. **Integrate Event Emission into State Machine** (In Progress)
   - Modify `OneshotStateMachine` to emit events on all state transitions
   - Add event emission to transition methods (`start`, `detect_silence`, `interrupt`, etc.)
   - Ensure events are emitted asynchronously without blocking state transitions

3. **Create Web Dashboard Interface** (Completed)
   - Set up FastAPI application for REST API endpoints
   - Implement WebSocket endpoint for real-time event streaming
   - Create HTML/CSS/JavaScript dashboard showing:
     - Live task list with current states
     - State transition timeline
     - Interrupt controls per task
     - System health metrics

4. **Implement TUI (Terminal User Interface)** (Completed)
   - Use `rich` library for terminal-based dashboard
   - Create interactive panels showing task status
   - Implement keyboard shortcuts for task interruption
   - Add real-time updates using asyncio event loops

5. **Update AsyncOrchestrator for UI Integration** (In Progress)
   - Add event emitter instance to orchestrator
   - Connect task state machines to central event system
   - Implement UI command handling (interrupt requests from dashboard)

6. **Add Configuration Options** (Pending)
   - CLI flags to enable/disable UI components
   - Configuration for web server port and TUI refresh rates
   - Environment variables for UI settings

7. **Update Tests** (In Progress)
   - Add tests for event emission correctness
   - Test WebSocket/real-time updates
   - Mock UI components for integration testing
   - Add end-to-end tests with both web and TUI interfaces

## Success Criteria
- Event system emits correct events for all state transitions without performance impact
- Web dashboard displays real-time task states and allows interruption
- TUI provides interactive monitoring with keyboard controls
- Both UI modes work concurrently with async task execution
- System remains stable under high event frequency
- All new tests pass and existing functionality preserved

## Testing Strategy
- **Unit Tests**: Test event emission in isolation, verify event payloads
- **Integration Tests**: Test full event flow from state machine to UI components
- **UI Tests**: Automated tests for web dashboard interactions using Selenium/Playwright
- **TUI Tests**: Test terminal interface with simulated user input
- **Performance Tests**: Benchmark event throughput and UI responsiveness
- **Load Tests**: Test with multiple concurrent tasks and UI clients

## Risk Assessment
- **Event Overhead**: Frequent event emission could impact performance; mitigation: async emission and configurable event filtering
- **UI Complexity**: Adding web/TUI interfaces increases codebase complexity; mitigation: modular design with clear separation of concerns
- **Real-time Requirements**: WebSocket/TUI updates must be responsive; mitigation: optimize event broadcasting and use efficient data structures
- **Security**: Web dashboard exposes control interfaces; mitigation: implement authentication and authorization
- **Cross-platform TUI**: Terminal interfaces vary by OS; mitigation: use cross-platform libraries and extensive testing
- **Dependency Bloat**: Additional UI libraries increase attack surface; mitigation: minimal dependencies, regular security audits