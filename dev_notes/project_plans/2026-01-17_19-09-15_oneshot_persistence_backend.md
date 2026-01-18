# Project Plan: Oneshot Persistence Backend

## Objective
Implement a SQLite-based persistence layer that saves task states, state transitions, and log fragments to enable crash recovery and task history. This will allow the Oneshot orchestrator to resume interrupted tasks after system restarts and provide a queryable history of task executions.

## Implementation Steps

1. **Design Database Schema**
   - Create SQLite tables for: `tasks` (task metadata), `task_states` (state transition history), `log_fragments` (captured output chunks)
   - Define indexes for efficient querying by task_id, timestamps, and state
   - Implement database migration system using alembic or similar

2. **Create Persistence Manager Class**
   - Build `PersistenceManager` class with async methods for database operations
   - Implement connection pooling and transaction management
   - Add methods for saving/loading task states and log data

3. **Integrate Persistence into State Machine**
   - Modify `OneshotStateMachine` to emit persistence events on state transitions
   - Add async persistence calls to transition methods without blocking
   - Implement state recovery logic to restore machine state from database

4. **Update AsyncOrchestrator for Persistence**
   - Add `PersistenceManager` instance to orchestrator initialization
   - Implement task recovery on startup: scan database for incomplete tasks and resume them
   - Add periodic log flushing to prevent memory bloat during long-running tasks

5. **Implement Log Fragment Storage**
   - Modify stream reading to batch and persist log chunks periodically
   - Add log retrieval methods for task history queries
   - Implement log rotation/cleanup for old entries

6. **Add Crash Recovery Logic**
   - Create recovery manager that identifies tasks in RUNNING/IDLE states on startup
   - Implement task resurrection: recreate process handles and attach to event loops
   - Handle edge cases like missing processes or corrupted state data

7. **Update CLI and Configuration**
   - Add CLI flags for enabling/disabling persistence
   - Configuration options for database path, retention policies, and recovery behavior
   - Environment variables for persistence settings

8. **Add Persistence Tests**
   - Unit tests for database operations and schema integrity
   - Integration tests for state persistence and recovery
   - Test crash simulation and recovery scenarios

## Success Criteria
- All task states and transitions are reliably saved to SQLite without performance impact
- Log fragments are captured and retrievable for completed and running tasks
- System can recover from crashes and resume interrupted tasks automatically
- Database queries are efficient even with large task histories
- Existing functionality remains intact when persistence is disabled
- All new tests pass and integration with async orchestrator works correctly

## Testing Strategy
- **Unit Tests**: Test database schema, CRUD operations, and persistence manager methods
- **Integration Tests**: Test full persistence flow from state machine to database and back
- **Recovery Tests**: Simulate crashes and verify task resurrection works correctly
- **Performance Tests**: Benchmark persistence operations under load and ensure no blocking
- **Data Integrity Tests**: Verify database consistency after various failure scenarios
- **Migration Tests**: Test schema updates and data preservation across versions

## Risk Assessment
- **Performance Impact**: Database writes could slow down state transitions; mitigation: async writes and batching
- **Database Corruption**: SQLite files could become corrupted; mitigation: WAL mode, regular backups, integrity checks
- **Memory Usage**: Storing logs in memory before flushing; mitigation: configurable batch sizes and memory limits
- **Recovery Complexity**: Resuming processes after crash is complex; mitigation: careful state validation and fallback modes
- **Data Growth**: Logs and history accumulating indefinitely; mitigation: configurable retention policies and cleanup jobs
- **Thread Safety**: Async operations accessing SQLite; mitigation: proper connection management and locking