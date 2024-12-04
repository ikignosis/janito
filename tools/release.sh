#!/bin/bash
set -e  # Exit on error

# Get current version from pyproject.toml
CURRENT_VERSION=$(grep -Po '(?<=version = ")[^"]*' pyproject.toml)
echo "Current version in pyproject.toml: $CURRENT_VERSION"

# Get latest version from PyPI using simpler regex pattern
PYPI_VERSION=$(pip index versions janito 2>/dev/null | grep -Po '(?<=janito \()[0-9.]+' | head -n1 || echo "not found")
echo "Current version on PyPI: $PYPI_VERSION"

# Prompt for new version
read -p "Enter new version: " NEW_VERSION

# Update version in pyproject.toml only (setup.py and __init__.py will read from it)
sed -i "s/version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml

echo "Version updated to $NEW_VERSION"

echo "Cleaning previous build artifacts..."
rm -rf dist/ build/ *.egg-info

echo "Building package..."
python -m build

python -m twine upload dist/*

echo "Release completed successfully!"