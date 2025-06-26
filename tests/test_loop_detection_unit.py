"""Unit tests for infinite loop detection logic."""

from prompter.config import PrompterConfig


class TestLoopDetectionUnit:
    """Unit tests for loop detection functionality."""

    def test_executed_tasks_tracking(self, temp_dir):
        """Test that executed tasks are properly tracked."""
        config_content = """[[tasks]]
name = "task1"
prompt = "Task 1"
verify_command = "true"

[[tasks]]
name = "task2"
prompt = "Task 2"
verify_command = "true"
"""
        config_file = temp_dir / "test.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)

        # Simulate the executed_tasks tracking from main.py
        executed_tasks = set()

        # First execution of task1
        assert "task1" not in executed_tasks
        executed_tasks.add("task1")

        # Second attempt at task1 should be detected
        assert "task1" in executed_tasks

        # task2 should not be in executed yet
        assert "task2" not in executed_tasks

    def test_loop_scenario_simulation(self, temp_dir, caplog):
        """Test simulation of loop detection with logging."""
        config_content = """[[tasks]]
name = "build"
prompt = "Build project"
verify_command = "true"
on_success = "test"

[[tasks]]
name = "test"
prompt = "Test project"
verify_command = "true"
on_success = "build"  # Creates a loop
"""
        config_file = temp_dir / "loop.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)

        # Simulate execution with loop detection
        executed_tasks = set()
        task_sequence = []

        # Start with first task
        current_task = config.tasks[0]

        # Simulate execution loop
        for _ in range(5):  # Limit iterations to prevent actual infinite loop
            if current_task.name in executed_tasks:
                # This is what should happen - detect the loop
                task_sequence.append(f"SKIP:{current_task.name}")
                break

            executed_tasks.add(current_task.name)
            task_sequence.append(f"EXEC:{current_task.name}")

            # Get next task based on success
            if current_task.on_success in ["stop", "next", "retry", "repeat"]:
                break

            # Find the next task
            next_task = None
            for task in config.tasks:
                if task.name == current_task.on_success:
                    next_task = task
                    break

            if next_task:
                current_task = next_task
            else:
                break

        # Verify the sequence
        assert task_sequence == ["EXEC:build", "EXEC:test", "SKIP:build"]

    def test_repeat_vs_task_jump(self, temp_dir):
        """Test that 'repeat' behaves differently from task name jumps."""
        config_content = """[[tasks]]
name = "repeat_task"
prompt = "Task with repeat"
verify_command = "true"
on_success = "repeat"

[[tasks]]
name = "jump_task"
prompt = "Task that jumps to itself"
verify_command = "true"
on_success = "jump_task"
"""
        config_file = temp_dir / "repeat_vs_jump.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)

        # Test repeat behavior
        repeat_task = config.tasks[0]
        assert repeat_task.on_success == "repeat"

        # Test self-jump
        jump_task = config.tasks[1]
        assert jump_task.on_success == "jump_task"

        # In actual execution:
        # - "repeat" should allow re-execution by removing from executed_tasks
        # - "jump_task" should be blocked on second attempt

    def test_complex_workflow_path_tracking(self, temp_dir):
        """Test tracking execution path in complex workflows."""
        config_content = """[[tasks]]
name = "start"
prompt = "Start"
verify_command = "true"
on_success = "check"

[[tasks]]
name = "check"
prompt = "Check condition"
verify_command = "test -f marker"
on_success = "success_path"
on_failure = "error_path"

[[tasks]]
name = "success_path"
prompt = "Success"
verify_command = "true"
on_success = "stop"

[[tasks]]
name = "error_path"
prompt = "Handle error"
verify_command = "true"
on_success = "check"  # Could create loop

[[tasks]]
name = "cleanup"
prompt = "Cleanup"
verify_command = "true"
on_success = "stop"
"""
        config_file = temp_dir / "complex.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)

        # Simulate failure path that loops back
        executed_tasks = set()
        path = []

        # Execute: start -> check (fail) -> error_path -> check (would loop)
        tasks_to_execute = ["start", "check", "error_path", "check"]

        for task_name in tasks_to_execute:
            if task_name in executed_tasks:
                path.append(f"BLOCKED:{task_name}")
                break
            executed_tasks.add(task_name)
            path.append(task_name)

        assert path == ["start", "check", "error_path", "BLOCKED:check"]

    def test_self_reference_detection(self, temp_dir):
        """Test detection of immediate self-references."""
        config_content = """[[tasks]]
name = "self_ref"
prompt = "Self referencing task"
verify_command = "true"
on_failure = "self_ref"
max_attempts = 1
"""
        config_file = temp_dir / "self_ref.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)
        task = config.tasks[0]

        # Task references itself
        assert task.on_failure == task.name

        # This should be handled by executed_tasks tracking
        executed_tasks = set()

        # First execution
        executed_tasks.add(task.name)

        # Second attempt should be blocked
        assert task.name in executed_tasks

    def test_validate_termination_paths(self, temp_dir):
        """Test that we can validate workflows have termination paths."""
        config_content = """[[tasks]]
name = "task1"
prompt = "Task 1"
verify_command = "true"
on_success = "task2"
on_failure = "stop"

[[tasks]]
name = "task2"
prompt = "Task 2"
verify_command = "true"
on_success = "task3"
on_failure = "task1"  # Back reference

[[tasks]]
name = "task3"
prompt = "Task 3"
verify_command = "true"
on_success = "stop"  # Termination
on_failure = "stop"  # Termination
"""
        config_file = temp_dir / "termination.toml"
        config_file.write_text(config_content)

        config = PrompterConfig(config_file)

        # Check that at least one task has a termination condition
        has_termination = False
        for task in config.tasks:
            if task.on_success == "stop" or task.on_failure == "stop":
                has_termination = True
                break

        assert has_termination, (
            "Workflow should have at least one termination condition"
        )
