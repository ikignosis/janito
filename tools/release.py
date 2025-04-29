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


def print_info(msg):
    print(f"{GREEN}[INFO]{NC} {msg}")


def print_warning(msg):
    print(f"{YELLOW}[WARNING]{NC} {msg}")


def print_error(msg):
    print(f"{RED}[ERROR]{NC} {msg}")
    sys.exit(1)


def check_tool(tool):
    if shutil.which(tool) is None:
        print_error(f"{tool} is not installed. Please install it first.")


def get_version_from_pyproject():
    if not os.path.isfile("pyproject.toml"):
        print_error(
            "pyproject.toml not found. Are you running this from the project root?"
        )
    with open("pyproject.toml", encoding="utf-8") as f:
        for line in f:
            m = re.match(r'^version = "([0-9]+\.[0-9]+\.[0-9]+)"', line.strip())
            if m:
                return m.group(1)
    print_error("Could not find version in pyproject.toml")


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
                        f"Version {project_version} already exists on PyPI. Please update the version in pyproject.toml."
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


def get_git_tag_for_version(version):
    tag_v = f"v{version}"
    tag_raw = version
    for tag in [tag_v, tag_raw]:
        try:
            subprocess.run(
                ["git", "rev-parse", tag],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return tag
        except subprocess.CalledProcessError:
            continue
    print_error(
        f"No git tag found matching version {version} (expected tag: {tag_v} or {tag_raw}). Please create the tag before running this script."
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
    check_tool("hatch")
    check_tool("twine")
    project_version = get_version_from_pyproject()
    print_info(f"Project version from pyproject.toml: {project_version}")
    check_version_on_pypi("janito", project_version)
    tag = get_git_tag_for_version(project_version)
    print_info(f"Found git tag: {tag}")
    check_tag_points_to_head(tag)
    # Remove site directory if it exists
    if os.path.isdir("site"):
        print_info("Removing site directory...")
        shutil.rmtree("site")
    # Remove dist directory
    if os.path.isdir("dist"):
        print_info("Removing old dist directory...")
        shutil.rmtree("dist")
    print_info("Building the package...")
    subprocess.run(["hatch", "build"], check=True)
    print_info("Publishing to PyPI...")
    subprocess.run(["twine", "upload", "dist/*"], shell=True, check=True)
    print_info("Release process completed successfully.")


if __name__ == "__main__":
    main()
