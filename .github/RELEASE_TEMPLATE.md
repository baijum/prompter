# Release Checklist for v0.x.x

**Release Date**: YYYY-MM-DD  
**Release Manager**: @username  
**Type**: Major / Minor / Patch

## Pre-release Checklist

### Code Quality
- [ ] All tests passing (`make test`)
- [ ] Linting passing (`make lint`)
- [ ] Type checking passing (`make type-check`)
- [ ] Code formatting checked (`make format-check`)
- [ ] Coverage acceptable (90%+)

### Documentation
- [ ] CHANGELOG.md updated with all changes
- [ ] Version bumped in pyproject.toml
- [ ] README.md badges/versions updated (if needed)
- [ ] Migration guide added (if breaking changes)
- [ ] Examples updated (if API changes)

### Review
- [ ] PR reviewed and approved
- [ ] No pending critical issues
- [ ] Dependencies up to date

## Release Execution

### Git Operations
- [ ] Release commit created with descriptive message
- [ ] Annotated tag created (`git tag -a v0.x.x -m "..."`)
- [ ] Tag pushed to GitHub (`git push origin v0.x.x`)
- [ ] Commits pushed to main branch

### GitHub Release
- [ ] GitHub release created with `gh release create`
- [ ] Release notes properly formatted
- [ ] Installation instructions included
- [ ] Migration guide linked (if applicable)

### PyPI Publishing
- [ ] Previous builds cleaned (`rm -rf dist/`)
- [ ] Distribution built (`python -m build`)
- [ ] Package uploaded to PyPI (`python -m twine upload dist/*`)

## Post-release Verification

### Installation Testing
- [ ] Clean virtual environment created
- [ ] Package installs correctly: `pip install claude-code-prompter==0.x.x`
- [ ] CLI works: `prompter --version`
- [ ] Basic functionality verified

### Documentation
- [ ] PyPI page shows new version
- [ ] GitHub release page is properly formatted
- [ ] Download stats working
- [ ] Documentation site updated (if applicable)

### Communication
- [ ] Release announced (if major version)
- [ ] Known issues documented
- [ ] Next version planning started

## Notes

### What's New in This Release
<!-- Summarize key features/fixes -->

### Known Issues
<!-- List any known issues -->

### Special Instructions
<!-- Any special deployment notes -->

### Rollback Plan
<!-- How to rollback if needed -->

---

**Sign-off**: [ ] Release completed successfully