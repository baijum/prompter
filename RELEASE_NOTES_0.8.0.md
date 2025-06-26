# Release Notes - v0.8.0

## Claude Session Resumption for Context Preservation

We're excited to announce the release of prompter v0.8.0, featuring a powerful new capability: **Claude session resumption**. This feature enables you to maintain full conversation context across multiple tasks, opening up new possibilities for complex, context-aware workflows.

### What's New

#### Session Resumption (`resume_previous_session`)

The new `resume_previous_session` task configuration option allows subsequent tasks to inherit the complete conversation history from previous tasks. This means Claude retains all understanding of:

- Code changes made in previous tasks
- Analysis and insights gathered
- Project structure and dependencies discovered
- Design decisions and rationale discussed

### Why This Matters

Previously, each task started with a fresh Claude session, requiring you to re-explain context or duplicate information across prompts. With session resumption, you can now:

1. **Build Progressive Workflows**: Start with analysis, then implement based on findings
2. **Maintain Consistency**: Ensure later tasks follow patterns established earlier
3. **Reduce Prompt Complexity**: Reference previous discussions without repetition
4. **Create Intelligent Pipelines**: Each task builds upon the knowledge of previous ones

### Example Usage

```toml
# First task: Analyze the codebase
[[tasks]]
name = "analyze_architecture"
prompt = "Analyze the current architecture and identify areas for improvement"
verify_command = "echo 'Analysis complete'"

# Second task: Implement improvements with full context
[[tasks]]
name = "refactor_based_on_analysis"
prompt = "Based on your analysis, refactor the identified problem areas"
resume_previous_session = true
verify_command = "python -m pytest"

# Third task: Document changes with complete understanding
[[tasks]]
name = "update_documentation"
prompt = "Update the documentation to reflect all changes made"
resume_previous_session = true
verify_command = "echo 'Docs updated'"
```

### Best Practices

- Use session resumption for related tasks that build upon each other
- Start new sessions for unrelated task groups to avoid context pollution
- Consider memory usage for very long task chains
- Test workflows incrementally to ensure context is properly maintained

### Getting Started

Update to v0.8.0:

```bash
pip install --upgrade claude-code-prompter
```

Then add `resume_previous_session = true` to any task that should inherit context from the previous task.

### What's Next

We're continuing to enhance prompter's workflow capabilities. Future releases will focus on:
- Parallel task execution
- Conditional context inheritance
- Session checkpointing and restoration
- Advanced workflow visualization

Thank you for using prompter! We're excited to see the complex workflows you'll build with session resumption.

---

**Full Changelog**: https://github.com/baijum/prompter/blob/main/CHANGELOG.md#080---2025-06-27
