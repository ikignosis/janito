#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import json

# Colors for output
GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[0;33m"
NC = "\033[0m"

# NOTE: Version is now determined from the latest git tag (vX.Y.Z or X.Y.Z)


def print_info(msg):
    print(f"{GREEN}[INFO]{NC} {msg}")


def print_warning(msg):
    print(f"{YELLOW}[WARNING]{NC} {msg}")


def print_error(msg):
    print(f"{RED}[ERROR]{NC} {msg}")
    sys.exit(1)


def check_tool(tool):
    if tool == "build":
        try:
            import importlib.util

            if importlib.util.find_spec("build") is None:
                print_error(
                    f"{tool} Python module is not installed. Please install it first."
                )
                sys.exit(1)
        except ImportError:
            print_error(
                f"{tool} Python module is not installed. Please install it first."
            )
            sys.exit(1)
    else:
        if tool == "twine":
            # Special handling for twine which might be installed as a module
            try:
                subprocess.run(
                    [sys.executable, "-m", "twine", "--version"],
                    check=False,
                    capture_output=True,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                print_error(f"{tool} is not installed. Please install it first.")
                sys.exit(1)
        elif shutil.which(tool) is None:
            print_error(f"{tool} is not installed. Please install it first.")
            sys.exit(1)


def get_latest_version_tag():
    # Get the latest tag matching semantic versioning (vX.Y.Z or X.Y.Z)
    try:
        tags = (
            subprocess.check_output(
                ["git", "tag", "--list", "v[0-9]*.[0-9]*.[0-9]*", "--sort=-v:refname"]
            )
            .decode()
            .split()
        )
        if not tags:
            tags = (
                subprocess.check_output(
                    [
                        "git",
                        "tag",
                        "--list",
                        "[0-9]*.[0-9]*.[0-9]*",
                        "--sort=-v:refname",
                    ]
                )
                .decode()
                .split()
            )
        if not tags:
            print_error("No version tags found in the repository.")
        latest_tag = tags[0]
        version = latest_tag.lstrip("v")
        return version, latest_tag
    except Exception as e:
        print_error(f"Error getting latest version tag: {e}")


def get_latest_pypi_version(pkg_name):
    url = f"https://pypi.org/pypi/{pkg_name}/json"
    try:
        with urllib.request.urlopen(url) as resp:
            data = json.load(resp)
            return data["info"]["version"]
    except Exception:
        return None


def version_tuple(v):
    return tuple(map(int, v.split(".")))


def check_version_on_pypi(pkg_name, project_version):
    print_info("Checking PyPI for version information...")
    latest_version = get_latest_pypi_version(pkg_name)
    if latest_version:
        print_info(f"Latest version on PyPI: {latest_version}")
        # Check if current version already exists on PyPI
        url = f"https://pypi.org/pypi/{pkg_name}/{project_version}/json"
        try:
            with urllib.request.urlopen(url) as resp:
                if resp.status == 200:
                    print_error(
                        f"Version {project_version} already exists on PyPI. Please create a new git tag with a higher version (vX.Y.Z) before releasing."
                    )
        except Exception:
            pass  # Not found is expected
        # Compare versions
        if version_tuple(project_version) < version_tuple(latest_version):
            print_error(
                f"Version {project_version} is older than the latest version {latest_version} on PyPI. Please update the version in pyproject.toml."
            )
        elif version_tuple(project_version) == version_tuple(latest_version):
            print_error(
                f"Version {project_version} is the same as the latest version {latest_version} on PyPI. Please update the version in pyproject.toml."
            )
    else:
        print_warning(
            "Could not fetch information from PyPI. Will attempt to publish anyway."
        )


def check_tag_points_to_head(tag):
    current_commit = (
        subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    )
    tag_commit = (
        subprocess.check_output(["git", "rev-list", "-n", "1", tag]).decode().strip()
    )
    if current_commit != tag_commit:
        print_error(
            f"Tag {tag} does not point to the current commit. Please update the tag or create a new one."
        )


def main():
    build_only = "--build-only" in sys.argv
    check_tool("build")
    check_tool("twine")

    # Check git status for uncommitted changes
    status = subprocess.check_output(["git", "status", "--porcelain"]).decode().strip()
    if status:
        print_error(
            "There are uncommitted changes in the working directory. Please commit or stash them before releasing.\n\nGit status output:\n"
            + status
        )

    project_version, tag = get_latest_version_tag()
    print_info(f"Project version from latest git tag: {project_version}")
    check_version_on_pypi("janito", project_version)
    print_info(f"Found git tag: {tag}")
    check_tag_points_to_head(tag)
    # Remove dist directory
    if os.path.isdir("dist"):
        print_info("Removing old dist directory...")
        shutil.rmtree("dist")
    print_info("Building the package...")
    subprocess.run([sys.executable, "-m", "build"], check=True)
    if build_only:
        print_info("Build completed (--build-only specified). Skipping upload to PyPI.")
        return
    print_info("Publishing to PyPI...")
    subprocess.run("twine upload dist/*", shell=True, check=True)
    print_info("Release process completed successfully.")


if __name__ == "__main__":
    main()
