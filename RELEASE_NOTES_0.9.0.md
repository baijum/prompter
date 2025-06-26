# Release Notes - v0.9.0

## 🎉 Introducing Task-Specific System Prompts

Prompter v0.9.0 brings a powerful new feature that gives you fine-grained control over Claude's behavior for individual tasks. With the new `system_prompt` configuration option, you can now customize how Claude approaches each task in your workflow.

## ✨ What's New

### System Prompts for Task Customization

The `system_prompt` field allows you to:

- **Enforce Planning**: Make Claude create detailed plans before executing changes
- **Set Expertise Context**: Define Claude as a domain expert for specific tasks
- **Add Safety Constraints**: Ensure careful handling of critical operations
- **Control Output Style**: Customize how Claude approaches and communicates

### Example Usage

```toml
[[tasks]]
name = "database_migration"
prompt = "Migrate the user authentication tables to the new schema"
system_prompt = "You are a database architect. Before making ANY changes, create a detailed migration plan including: 1) Backup strategy, 2) Step-by-step migration process, 3) Rollback procedure, 4) Testing approach. Present this plan and wait for approval before proceeding."
verify_command = "python manage.py check_migrations"
```

### New Example Workflows

We've added three comprehensive example workflows that demonstrate the power of system prompts:

1. **Planning Workflow** (`examples/planning-workflow.toml`)
   - Shows how to enforce planning before implementation
   - Multi-phase approach: analyze → plan → implement → verify

2. **Safe Production Deploy** (`examples/safe-production-deploy.toml`)
   - Production deployment with extensive safety checks
   - Different system prompts for each deployment phase
   - Includes rollback planning and incident reporting

3. **Code Review Workflow** (`examples/code-review-workflow.toml`)
   - Multi-perspective automated code review
   - Security, performance, and maintainability reviews
   - Auto-fix for critical issues

## 🔧 Configuration

Add the `system_prompt` field to any task:

```toml
[[tasks]]
name = "refactor_with_safety"
prompt = "Refactor the payment processing module"
system_prompt = "You are a senior engineer working on payment systems. Safety is paramount. Make minimal, testable changes. Document every decision."
verify_command = "make test"
```

## 💡 Best Practices

1. **Combine with Session Resumption**: Use different system prompts for different phases while maintaining context
2. **Be Specific**: Clear, detailed system prompts yield better results
3. **Safety First**: Use system prompts to add constraints for critical operations
4. **Progressive Enhancement**: Start simple, add complexity through system prompts

## 📈 What's Next

This feature opens up new possibilities for complex, multi-phase workflows. We're excited to see how you use system prompts to create more sophisticated automation pipelines.

## 🙏 Thank You

Thank you to our community for the continued feedback and support. Your input helps shape Prompter into a better tool for everyone.

---

**Full Changelog**: https://github.com/baijum/prompter/blob/main/CHANGELOG.md

**Documentation**: See the updated README for comprehensive examples and documentation on using system prompts.
