# Release Process

This document outlines the release process for the claude-code-prompter project.

## Prerequisites

Before creating a release, ensure you have:

1. **Push access** to the main repository
2. **PyPI account** with maintainer access to `claude-code-prompter`
3. **GitHub CLI** (`gh`) installed and authenticated
4. **Python build tools** installed:
   ```bash
   pip install build twine
   ```

## Versioning

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR** version (1.0.0): Breaking API changes
- **MINOR** version (0.1.0): New features, backward compatible
- **PATCH** version (0.0.1): Bug fixes, backward compatible

## Release Process

### 1. Prepare the Release

#### 1.1 Create a Feature Branch (if needed)
```bash
git checkout -b release/v0.x.x
```

#### 1.2 Update Version Number
Edit `pyproject.toml`:
```toml
version = "0.x.x"  # Update to new version
```

#### 1.3 Update CHANGELOG.md
Add a new section at the top following the existing format:
```markdown
## [0.x.x] - YYYY-MM-DD

### 🚀 Added
- New features...

### 🔧 Improved
- Improvements...

### 🐛 Fixed
- Bug fixes...

### 📚 Documentation
- Documentation updates...
```

#### 1.4 Run All Checks
```bash
# Run all quality checks and tests
make all

# This runs:
# - ruff check (linting)
# - ruff format --check (formatting)
# - mypy (type checking)
# - pytest (all tests)
# - coverage report
```

### 2. Create Release Commit and Tag

#### 2.1 Stage Changes
```bash
git add pyproject.toml CHANGELOG.md
```

#### 2.2 Create Release Commit
```bash
git commit -m "Release v0.x.x - Brief description

- Main feature or change
- Other significant changes
- Any breaking changes

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

#### 2.3 Create Annotated Tag
```bash
git tag -a v0.x.x -m "Release v0.x.x - Brief description"
```

### 3. Push and Create GitHub Release

#### 3.1 Push Tag to GitHub
```bash
git push origin v0.x.x
```

#### 3.2 Create GitHub Release
```bash
gh release create v0.x.x \
  --title "Release v0.x.x - Brief description" \
  --notes "$(cat <<'EOF'
## 🚀 What's New

Brief overview of the release...

## ✨ Highlights

- Major feature 1
- Major feature 2
- Important fix

## 📋 Full Changelog

[Paste relevant section from CHANGELOG.md]

## 📦 Installation

\`\`\`bash
pip install claude-code-prompter==0.x.x
\`\`\`

## 🔗 Links

- [Full Changelog](https://github.com/baijum/prompter/compare/v0.x.x-1...v0.x.x)
- [PyPI Package](https://pypi.org/project/claude-code-prompter/0.x.x/)
EOF
)"
```

### 4. Push Commits to Main

```bash
# If on a feature branch, create PR and merge
# Otherwise, push directly
git push origin main
```

### 5. Publish to PyPI

#### 5.1 Clean Previous Builds
```bash
rm -rf dist/ build/ *.egg-info/
```

#### 5.2 Build Distribution
```bash
python -m build
```

This creates:
- `dist/claude_code_prompter-0.x.x-py3-none-any.whl`
- `dist/claude_code_prompter-0.x.x.tar.gz`

#### 5.3 Upload to PyPI
```bash
# For test release (optional)
python -m twine upload --repository testpypi dist/*

# For production release
python -m twine upload dist/*
```

### 6. Post-Release Verification

#### 6.1 Verify PyPI Package
```bash
# In a fresh virtual environment
pip install claude-code-prompter==0.x.x
prompter --version
```

#### 6.2 Verify GitHub Release
- Check https://github.com/baijum/prompter/releases
- Ensure release notes are properly formatted
- Verify source code archives are attached

#### 6.3 Update Documentation (if needed)
- Update README.md badges if version changed
- Update any version-specific documentation

## Release Checklist Template

Copy this checklist for each release:

```markdown
## Release Checklist for v0.x.x

### Pre-release
- [ ] All tests passing (`make test`)
- [ ] Code quality checks passing (`make all`)
- [ ] CHANGELOG.md updated with release notes
- [ ] Version bumped in pyproject.toml
- [ ] Documentation updated (if needed)

### Release
- [ ] Release commit created
- [ ] Tag created (`git tag -a v0.x.x -m "..."`)
- [ ] Tag pushed to GitHub
- [ ] GitHub release created with `gh release create`
- [ ] Commits pushed to main branch

### Publishing
- [ ] Distribution built (`python -m build`)
- [ ] Package uploaded to PyPI (`python -m twine upload dist/*`)
- [ ] Installation verified in clean environment

### Post-release
- [ ] PyPI page shows new version
- [ ] GitHub release page is properly formatted
- [ ] Installation works: `pip install claude-code-prompter==0.x.x`
- [ ] Announce release (if applicable)
```

## Common Issues and Solutions

### 1. Tests Failing
- Run `make all` to see all issues
- Fix any linting issues with `ruff format .`
- Address type errors shown by mypy
- Ensure all new code has tests

### 2. PyPI Upload Errors
- Ensure you're authenticated: `python -m twine upload --username __token__`
- Check for existing version (can't overwrite)
- Verify package metadata in pyproject.toml

### 3. GitHub Release Issues
- Ensure `gh` is authenticated: `gh auth status`
- Tag must exist before creating release
- Use proper markdown formatting in release notes

## Emergency Procedures

### Rolling Back a Release

If a critical issue is found after release:

1. **Create a patch release** (preferred):
   ```bash
   # Fix the issue
   # Bump version to 0.x.x+1
   # Follow normal release process
   ```

2. **Delete and recreate** (last resort):
   ```bash
   # Delete GitHub release (keeps tag)
   gh release delete v0.x.x

   # Delete tag locally and remotely
   git tag -d v0.x.x
   git push origin :refs/tags/v0.x.x

   # Note: Cannot delete from PyPI - must create new version
   ```

## Automation Opportunities

Consider automating these steps in the future:
- Version bumping based on commit messages
- CHANGELOG generation from commit history
- Automated testing on release tags
- PyPI publishing via GitHub Actions

## Questions?

If you have questions about the release process:
1. Check existing releases for examples
2. Open an issue for clarification
3. Discuss in PR before making changes
