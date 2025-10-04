# Releasing Janito

This guide explains the release process for Janito, including how to create new releases and what the automated release script does.

## Prerequisites

Before you can create a release, you need to:

1. Set up a GitHub Personal Access Token (PAT):

   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Generate a new token with `repo` scope
   - Store it securely

2. Set the GITHUB_TOKEN environment variable:
   ```bash
   export GITHUB_TOKEN="your-token-here"
   ```

3. Install required Python packages:
   ```bash
   pip install requests twine build
   ```

## Release Process

The release process is automated through the `tools/release.py` script. Here's how it works:

### 1. Create a Git Tag

First, create a new git tag following semantic versioning (vX.Y.Z):

```bash
# Check current latest tag
git tag -l "v*" --sort=-v:refname | head -n 1

# Create new tag (increment patch version)
git tag vX.Y.Z

# Push the tag to remote
git push origin vX.Y.Z
```

### 2. Run the Release Script

Execute the release script:

```bash
python tools/release.py
```

To also create a GitHub release, use the `--gh-release` flag:

```bash
python tools/release.py --gh-release
```

The script will:

- Verify you have the required tools installed
- Check that there are no uncommitted changes
- Get the version from the latest git tag
- Verify the tag points to the current commit
- Build the package
- Upload to PyPI
- Create a GitHub release (only if `--gh-release` flag is used)

### 3. What the GitHub Release Includes

The automated GitHub release will:

- Use the tag name as the release title
- Include a basic changelog message linking to CHANGELOG.md
- Be marked as a production release (not draft or prerelease)

## Build Only Mode

If you want to build the package without uploading it, use:

```bash
python tools/release.py --build-only
```

This is useful for testing the build process locally.

## Troubleshooting

Common issues and solutions:

- **GITHUB_TOKEN not set**: Make sure you've exported the environment variable
- **Tag doesn't point to current commit**: Make sure you're on the correct commit before tagging
- **Version already exists on PyPI**: Increment the version number in your tag
- **Uncommitted changes**: Commit or stash your changes before releasing