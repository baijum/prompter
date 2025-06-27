"""Constants used throughout the prompter application."""

# Timeout constants (in seconds)
DEFAULT_TASK_TIMEOUT = 300  # 5 minutes - default timeout for task execution
DEFAULT_VERIFICATION_TIMEOUT = 300  # 5 minutes - timeout for verification commands
DEFAULT_INIT_TIMEOUT = 120  # 2 minutes - default timeout for AI project analysis
DEFAULT_CHECK_INTERVAL = 5  # 5 seconds - delay between task completion and verification

# Safety limits
MAX_TASK_ITERATIONS = 1000  # Maximum iterations to prevent runaway loops
