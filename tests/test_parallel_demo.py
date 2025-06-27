"""Demonstration test for parallel execution feature."""

import tempfile
from pathlib import Path

import pytest

from prompter.config import PrompterConfig


@pytest.mark.integration
class TestParallelExecutionDemo:
    """Demonstration of parallel execution capabilities."""

    def test_parallel_execution_workflow_demo(self):
        """Demonstrate a complete parallel execution workflow."""
        # Create a realistic workflow configuration
        config_content = """
[settings]
max_parallel_tasks = 4
enable_parallel = true
check_interval = 0

# Stage 1: Initial setup
[[tasks]]
name = "setup_environment"
prompt = "Set up development environment"
verify_command = "echo 'Environment ready'"
depends_on = []

# Stage 2: Parallel analysis (3 tasks can run simultaneously)
[[tasks]]
name = "analyze_frontend"
prompt = "Analyze frontend code for issues"
verify_command = "echo 'Frontend analyzed'"
depends_on = ["setup_environment"]

[[tasks]]
name = "analyze_backend"
prompt = "Analyze backend code for issues"
verify_command = "echo 'Backend analyzed'"
depends_on = ["setup_environment"]

[[tasks]]
name = "analyze_database"
prompt = "Analyze database schema and queries"
verify_command = "echo 'Database analyzed'"
depends_on = ["setup_environment"]

# Stage 3: Fix issues (depends on analysis)
[[tasks]]
name = "fix_frontend_issues"
prompt = "Fix the frontend issues found during analysis"
verify_command = "echo 'Frontend fixed'"
depends_on = ["analyze_frontend"]

[[tasks]]
name = "fix_backend_issues"
prompt = "Fix the backend issues found during analysis"
verify_command = "echo 'Backend fixed'"
depends_on = ["analyze_backend"]

[[tasks]]
name = "optimize_database"
prompt = "Optimize database based on analysis"
verify_command = "echo 'Database optimized'"
depends_on = ["analyze_database"]

# Stage 4: Integration testing (after fixes)
[[tasks]]
name = "integration_tests"
prompt = "Run full integration test suite"
verify_command = "echo 'Tests passed'"
depends_on = ["fix_frontend_issues", "fix_backend_issues", "optimize_database"]

# Stage 5: Deploy
[[tasks]]
name = "deploy_to_staging"
prompt = "Deploy the application to staging"
verify_command = "echo 'Deployed to staging'"
depends_on = ["integration_tests"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_file = Path(f.name)

        try:
            # Load and validate configuration
            config = PrompterConfig(config_file)
            errors = config.validate()
            assert len(errors) == 0, f"Config validation failed: {errors}"

            # Build and visualize the task graph
            graph = config.build_task_graph()

            # Print the execution plan
            print("\n" + "=" * 60)
            print("PARALLEL EXECUTION WORKFLOW DEMONSTRATION")
            print("=" * 60)
            print(graph.visualize_ascii())

            # Show execution levels
            levels = graph.get_execution_levels()
            print("\nExecution Timeline:")
            print("-" * 60)

            total_time = 0
            for i, level_tasks in enumerate(levels):
                print(f"\nTime {total_time}: Stage {i + 1}")
                print(f"  Running in parallel: {', '.join(level_tasks)}")
                print(
                    f"  Max concurrent tasks: {min(len(level_tasks), config.max_parallel_tasks)}"
                )
                total_time += 1

            print(f"\nTotal execution time: ~{total_time} time units")
            print(f"Sequential execution would take: {len(config.tasks)} time units")
            print(f"Speedup factor: {len(config.tasks) / total_time:.1f}x")

            # Demonstrate dependency checking
            print("\nDependency Analysis:")
            print("-" * 60)

            # Check what tasks are ready at different stages
            completed = set()
            for stage in range(len(levels)):
                ready = graph.get_ready_tasks(completed)
                print(f"Stage {stage + 1}: Ready tasks = {ready}")
                completed.update(levels[stage])

            # Show critical path
            critical_path = graph.get_critical_path()
            print("\nCritical Path (longest dependency chain):")
            print(" -> ".join(critical_path))
            print(f"Minimum possible execution time: {len(critical_path)} time units")

        finally:
            config_file.unlink()

    def test_parallel_vs_sequential_comparison(self):
        """Compare parallel vs sequential execution characteristics."""
        # Create a wide workflow with many parallel opportunities
        num_modules = 6
        config_content = f"""
[settings]
max_parallel_tasks = 3
enable_parallel = true

# Analyze {num_modules} independent modules
"""

        for i in range(1, num_modules + 1):
            config_content += f"""
[[tasks]]
name = "analyze_module_{i}"
prompt = "Analyze module {i}"
verify_command = "echo 'Module {i} analyzed'"
depends_on = []
"""

        # Add aggregation task
        deps = [f'"analyze_module_{i}"' for i in range(1, num_modules + 1)]
        config_content += f"""
[[tasks]]
name = "create_report"
prompt = "Create comprehensive analysis report"
verify_command = "echo 'Report created'"
depends_on = [{", ".join(deps)}]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_file = Path(f.name)

        try:
            config = PrompterConfig(config_file)
            graph = config.build_task_graph()

            print("\n" + "=" * 60)
            print("PARALLEL VS SEQUENTIAL COMPARISON")
            print("=" * 60)

            # Calculate execution times
            levels = graph.get_execution_levels()
            parallel_time = len(levels)
            sequential_time = len(config.tasks)

            print(
                f"\nWorkflow: {num_modules} independent analysis tasks + 1 aggregation task"
            )
            print(f"Max parallel tasks: {config.max_parallel_tasks}")
            print(f"\nSequential execution: {sequential_time} time units")
            print(f"Parallel execution: {parallel_time} time units")
            print(
                f"Time saved: {sequential_time - parallel_time} time units ({(1 - parallel_time / sequential_time) * 100:.0f}%)"
            )
            print(f"Speedup: {sequential_time / parallel_time:.1f}x faster")

            # Show execution pattern
            print("\nParallel Execution Pattern:")
            for i, level_tasks in enumerate(levels):
                batches = [
                    level_tasks[j : j + config.max_parallel_tasks]
                    for j in range(0, len(level_tasks), config.max_parallel_tasks)
                ]
                for batch_num, batch in enumerate(batches):
                    print(f"  Time {i}.{batch_num}: {', '.join(batch)}")

        finally:
            config_file.unlink()


if __name__ == "__main__":
    # Run the demo when executed directly
    demo = TestParallelExecutionDemo()
    demo.test_parallel_execution_workflow_demo()
    print("\n" * 2)
    demo.test_parallel_vs_sequential_comparison()
