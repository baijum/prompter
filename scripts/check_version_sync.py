#!/usr/bin/env python3
"""Check that version numbers are synchronized between pyproject.toml and __init__.py."""

import re
import sys
from pathlib import Path


def get_version_from_pyproject():
    """Extract version from pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    if not pyproject_path.exists():
        print(f"Error: {pyproject_path} not found")
        return None

    with open(pyproject_path) as f:
        content = f.read()

    # Look for version = "x.y.z" pattern
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    if match:
        return match.group(1)

    print("Error: Could not find version in pyproject.toml")
    return None


def get_version_from_init():
    """Extract version from src/prompter/__init__.py."""
    init_path = Path(__file__).parent.parent / "src" / "prompter" / "__init__.py"
    if not init_path.exists():
        print(f"Error: {init_path} not found")
        return None

    with open(init_path) as f:
        content = f.read()

    # Look for __version__ = "x.y.z" pattern
    match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    if match:
        return match.group(1)

    print("Error: Could not find __version__ in __init__.py")
    return None


def main():
    """Check version synchronization."""
    pyproject_version = get_version_from_pyproject()
    init_version = get_version_from_init()

    if pyproject_version is None or init_version is None:
        return 1

    if pyproject_version != init_version:
        print("❌ Version mismatch detected!")
        print(f"   pyproject.toml: {pyproject_version}")
        print(f"   __init__.py:    {init_version}")
        print()
        print("Please update both files to have the same version.")
        return 1

    print(f"✅ Version {pyproject_version} is synchronized correctly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
