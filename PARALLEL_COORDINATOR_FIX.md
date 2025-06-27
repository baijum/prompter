# Parallel Coordinator Bug Fix

## Issue
Tests that verified `max_parallel_tasks` limit enforcement were hanging indefinitely. The hang occurred specifically when:
- Multiple tasks had no dependencies (all could run immediately)
- The number of tasks exceeded `max_parallel_tasks` limit
- Tasks would get stuck and never complete

## Root Cause
The bug was in the `_get_ready_tasks()` method in `parallel_coordinator.py`:

```python
# BEFORE (buggy code):
def _get_ready_tasks(self) -> list[str]:
    ready = []
    for name, state in self.task_states.items():
        if state.status == TaskStatus.PENDING:  # <-- BUG: Only checks PENDING
            # Check dependencies...
            if all(status == TaskStatus.COMPLETED for status in dep_states):
                ready.append(name)
                state.status = TaskStatus.READY  # <-- Changes to READY
```

The issue:
1. When a task's dependencies are satisfied, it changes from PENDING → READY
2. If the task can't be scheduled immediately (due to max_parallel_tasks limit), it stays in READY state
3. On the next scheduler iteration, the method only checks PENDING tasks
4. Tasks stuck in READY state are never reconsidered for scheduling
5. This causes a deadlock where tasks remain unscheduled forever

## Solution
Modified `_get_ready_tasks()` to also consider tasks already in READY state:

```python
# AFTER (fixed code):
def _get_ready_tasks(self) -> list[str]:
    ready = []
    for name, state in self.task_states.items():
        # If already marked as ready, include it
        if state.status == TaskStatus.READY:
            ready.append(name)
            continue

        # Check pending tasks for readiness
        if state.status == TaskStatus.PENDING:
            # Check dependencies...
```

## Tests Fixed
- `test_parallel_integration.py::test_max_parallel_tasks_limit` ✅
- `test_parallel_integration_simple.py::test_parallel_limit_respected` ✅

## Test Results
All 12 slow integration tests now pass:
```
================ 12 passed, 2 deselected, 14 warnings in 3.50s =================
```

## Key Insight
The bug only manifested when tasks had no dependencies because:
- Tasks with dependencies naturally get scheduled one at a time as dependencies complete
- Tasks without dependencies all become READY at once, exposing the scheduling bug
- This explains why other parallel tests with dependencies worked fine
