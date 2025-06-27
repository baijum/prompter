# Progress Visualization Implementation Plan

## Architecture Overview

### Core Components

1. **ProgressDisplay Class**
   - Main orchestrator for terminal UI
   - Manages rich.Live display context
   - Handles updates from parallel tasks
   - Thread-safe update queue

2. **TaskProgressTracker**
   - Tracks individual task progress
   - Estimates completion time
   - Manages task state transitions
   - Calculates progress percentages

3. **Integration Layer**
   - Hooks into ParallelTaskCoordinator
   - Intercepts task state changes
   - Provides progress callbacks
   - Handles graceful shutdown

### Display Components

```python
class ProgressDisplay:
    """Rich terminal display for parallel task execution."""

    def __init__(self, config: PrompterConfig):
        self.config = config
        self.console = Console()
        self.live = Live(console=self.console, refresh_per_second=4)
        self.task_progress = {}
        self.start_time = time.time()
        self._update_lock = threading.Lock()

    def create_layout(self) -> Layout:
        """Create the main layout with panels."""
        # Header panel
        # Active tasks table
        # Waiting tasks panel
        # Summary statistics
        pass

    def update_task_progress(self, task_name: str, status: TaskStatus,
                           progress: float = 0, message: str = ""):
        """Thread-safe task progress update."""
        with self._update_lock:
            self.task_progress[task_name] = {
                'status': status,
                'progress': progress,
                'message': message,
                'updated': time.time()
            }
```

### Progress Tracking Strategy

1. **Task Lifecycle Events**
   - `PENDING`: Gray, no progress bar
   - `READY`: Yellow, "Waiting to start"
   - `RUNNING`: Blue progress bar with percentage
   - `COMPLETED`: Green checkmark
   - `FAILED`: Red X with error snippet

2. **Progress Estimation**
   - Use verification command output parsing
   - Track subtask completion (if available)
   - Time-based estimation for unknown progress
   - Historical data for better estimates

3. **Dependency Visualization**
   - Show blocking tasks for waiting items
   - Highlight critical path
   - Display estimated wait time

### Implementation Phases

## Phase 1: Basic Infrastructure (Day 1 Morning)

1. **Add rich dependency**
   ```toml
   [dependencies]
   rich = ">=13.0.0"
   ```

2. **Create progress module**
   - `src/prompter/progress_display.py`
   - Basic ProgressDisplay class
   - Simple task status tracking

3. **Integration hooks**
   - Add callbacks to ParallelTaskCoordinator
   - Pass progress updates to display

## Phase 2: Rich UI Components (Day 1 Afternoon)

1. **Layout Design**
   - Header with workflow info
   - Active tasks table with progress bars
   - Waiting tasks list
   - Summary statistics

2. **Live Updates**
   - Implement smooth refresh
   - Handle terminal resize
   - Manage update frequency

3. **Visual Polish**
   - Color coding for states
   - Icons and symbols
   - Responsive column widths

## Phase 3: Advanced Features (Day 2 Morning)

1. **Progress Intelligence**
   - Parse Claude output for progress hints
   - Estimate completion times
   - Show subtask progress

2. **Dependency Insights**
   - Visual dependency chains
   - Critical path highlighting
   - Bottleneck identification

3. **Performance Metrics**
   - Task duration tracking
   - Resource utilization display
   - Parallel efficiency metrics

## Phase 4: Integration & Polish (Day 2 Afternoon)

1. **CLI Integration**
   - Add --progress flag (default: auto)
   - Add --no-progress flag
   - Add --simple-progress for basic output

2. **Compatibility**
   - Detect terminal capabilities
   - Fallback to simple progress
   - CI/CD friendly output

3. **Testing & Documentation**
   - Unit tests for display logic
   - Integration tests
   - Update README with examples

### Key Design Decisions

1. **Update Frequency**: 4 Hz (250ms) for smooth updates without flicker
2. **Thread Safety**: Lock-based updates from parallel tasks
3. **Memory Efficiency**: Ring buffer for completed tasks (show last 10)
4. **Terminal Detection**: Auto-disable in non-TTY environments
5. **Graceful Degradation**: Falls back to simple progress bars

### Error Handling

1. **Terminal Issues**
   - Catch rich exceptions
   - Fall back to print statements
   - Continue execution without progress

2. **Performance Impact**
   - Throttle updates if too frequent
   - Batch updates when possible
   - Disable for very fast tasks

3. **Thread Safety**
   - Use locks for shared state
   - Queue updates if needed
   - Handle race conditions

### Success Metrics

1. **User Experience**
   - Clear understanding of execution state
   - No terminal flicker or artifacts
   - Responsive to terminal resize

2. **Performance**
   - < 1% CPU overhead
   - < 10MB memory usage
   - No impact on task execution

3. **Compatibility**
   - Works on Windows, macOS, Linux
   - Supports common terminals
   - Graceful CI/CD behavior
