# Test Markers Summary

This document summarizes the pytest markers applied to tests in the prompter project.

## Markers Applied

### @pytest.mark.slow

Applied to tests that involve time delays or significant processing:

1. **test_parallel_execution.py**
   - `test_parallel_execution_respects_dependencies` - Contains `time.sleep(0.1)` to simulate work

2. **test_progress_display.py**
   - `test_thread_safety` - Uses multiple threads with `time.sleep(0.001)` delays

3. **test_parallel_integration.py**
   - Entire `TestParallelIntegration` class - Complex integration tests with multiple sleep calls

### @pytest.mark.integration

Applied to integration tests that test multiple components together:

1. **test_parallel_integration.py**
   - Entire `TestParallelIntegration` class - Tests parallel execution with real-world scenarios

2. **test_parallel_integration_simple.py**
   - Entire `TestParallelExecutionIntegration` class - Integration tests for parallel execution

3. **test_parallel_demo.py**
   - Entire `TestParallelExecutionDemo` class - Demonstration of parallel execution capabilities

4. **test_integration.py**
   - Entire `TestEndToEndIntegration` class - End-to-end integration tests

## Running Tests

To run tests excluding slow tests:
```bash
pytest -m "not slow"
```

To run tests excluding integration tests:
```bash
pytest -m "not integration"
```

To run only unit tests (excluding both slow and integration):
```bash
pytest -m "not slow and not integration"
```

To run only slow tests:
```bash
pytest -m slow
```

To run only integration tests:
```bash
pytest -m integration
```

## Notes

- The `slow` marker is applied to individual tests that have time delays
- The `integration` marker is applied to entire test classes that test multiple components
- Some tests have both markers (e.g., `TestParallelIntegration` class)
- These markers help in CI/CD pipelines where you might want to run quick unit tests frequently and slower integration tests less often
