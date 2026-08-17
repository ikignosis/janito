"""Plugin listing, installation and uninstallation CLI handlers."""

import re
import shutil
import tempfile
import zipfile
from pathlib import Path

import requests

from ...plugin_manager import (
    LOADED_PLUGINS,
    get_default_plugins_dir,
    scan_installed_plugins,
)


def handle_list_plugins(args) -> int:
    """Handle --list-plugins command.

    Displays the plugins loaded via ``--plugin`` and autoloaded from
    ``~/.janito/plugins`` (registered by ``janito.plugin_manager.load_plugins``
    / ``load_installed_plugins``) and any ``on_start`` errors.

    Args:
        args: Parsed command line arguments (unused).

    Returns:
        int: Exit code (0 on success).
    """
    from rich.console import Console
    from rich.table import Table

    console = Console(markup=False)

    if not LOADED_PLUGINS:
        table = Table(
            title="Loaded Plugins",
            title_style="bold",
            show_header=False,
            box=None,
            pad_edge=False,
        )
        table.add_column("Key", style="green", no_wrap=True)
        table.add_column("Value", overflow="fold")
        table.add_row("Status", "No plugins loaded.")
        table.add_row("Load a plugin", "janito --plugin <plugin_dir>")
        table.add_row("Install a plugin", "janito --install-plugin <github_url>")
        table.add_row("Uninstall a plugin", "janito --uninstall-plugin <plugin_name>")
        console.print(table)
        return 0

    table = Table(
        title="Loaded Plugins",
        title_style="bold",
        header_style="bold cyan",
    )
    table.add_column("Plugin", style="green", no_wrap=True)
    table.add_column("Path", overflow="fold")
    table.add_column("Status", no_wrap=True)

    for plugin in LOADED_PLUGINS:
        if plugin.load_error is None:
            status = "OK"
        else:
            status = f"ERROR: {plugin.load_error}"
        table.add_row(plugin.name, str(plugin.path), status)

    console.print(table)
    return 0


def _parse_github_repo_url(url: str) -> tuple[str, str]:
    """Parse a GitHub repository URL to extract owner and repo.

    Args:
        url: GitHub URL (e.g., https://github.com/joaompinto/janito-codesearch-plugin)

    Returns:
        Tuple of (owner, repo)

    Raises:
        ValueError: If the URL is not a valid GitHub repository URL
    """
    # Pattern: https://github.com/{owner}/{repo} (optionally with .git suffix)
    pattern = r"(?:https?://)?github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$"
    match = re.match(pattern, url)

    if not match:
        raise ValueError(f"Invalid GitHub repository URL format: {url}")

    owner, repo = match.groups()
    return owner, repo


def _download_zip(url: str, dest_path: Path) -> bool:
    """Download ``url`` to ``dest_path``; returns False on failure."""
    print(f"Downloading {url}...")
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error downloading: {e}")
        return False

    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print("Download complete.")
    print()
    return True


def _extract_zip(zip_path: Path, dest_dir: Path) -> bool:
    """Extract a zip archive to ``dest_dir``; returns False on failure."""
    print(f"Extracting to {dest_dir}...")
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest_dir)
    except zipfile.BadZipFile as e:
        print(f"Error extracting archive: {e}")
        return False
    return True


def handle_uninstall_plugin(name: str) -> int:
    """Uninstall a plugin by its plugin name.

    Removes the installed plugin whose ``name`` (the ``name`` symbol
    exported by the plugin's ``__init__.py``, as shown by
    ``--list-plugins``) matches ``name``.  For example, the codesearch
    plugin installs to ``~/.janito/plugins/janito-codesearch-plugin`` but
    its plugin name is ``codesearch``, so ``--uninstall-plugin codesearch``
    removes that directory.  Broken plugins that cannot be imported are
    matched by their directory name as a fallback.

    Args:
        name: Plugin name to uninstall.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    print(f"Uninstalling plugin: {name}")
    print()

    installed = scan_installed_plugins()
    matches = [path for plugin_name, path in installed if plugin_name == name]

    if not matches:
        print(f"Error: Plugin '{name}' not found.")
        print("Use --list-plugins to see installed plugins.")
        return 1

    plugin_path = matches[0]

    if plugin_path.exists():
        print(f"Removing plugin files from {plugin_path}...")
        shutil.rmtree(plugin_path)
        print("[OK] Plugin files removed.")
    else:
        print(f"Warning: Plugin directory not found at {plugin_path}")

    print()
    print(f"[OK] Plugin '{name}' uninstalled successfully!")

    return 0


def handle_install_plugin(url: str) -> int:
    """Install a plugin from a GitHub URL.

    Downloads the repository's ``master`` zip archive from GitHub and
    extracts it to ``~/.janito/plugins/<repo-name>``.

    Args:
        url: GitHub repository URL.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    print(f"Installing plugin from: {url}")
    print()

    # Parse the GitHub URL
    try:
        owner, repo = _parse_github_repo_url(url)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    print(f"Repository: {owner}/{repo}")

    plugins_dir = get_default_plugins_dir()
    plugins_dir.mkdir(parents=True, exist_ok=True)
    plugin_dest = plugins_dir / repo

    if plugin_dest.exists():
        print(f"Removing existing plugin at {plugin_dest}...")
        shutil.rmtree(plugin_dest)

    # Download the master zip
    zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip"
    temp_dir = tempfile.mkdtemp(prefix="janito_plugin_")
    zip_path = Path(temp_dir) / f"{repo}.zip"

    try:
        if not _download_zip(zip_url, zip_path):
            return 1

        # Extract to temp dir, then move the extracted repo dir into place
        extract_dir = Path(temp_dir) / "extract"
        extract_dir.mkdir()
        if not _extract_zip(zip_path, extract_dir):
            return 1

        # GitHub master zips extract to <repo>-master/
        extracted = extract_dir / f"{repo}-master"
        if not extracted.is_dir():
            # Fallback: use whatever single top-level directory was created
            top_level = [d for d in extract_dir.iterdir() if d.is_dir()]
            if len(top_level) == 1:
                extracted = top_level[0]
            else:
                print(f"Error: unexpected zip structure in {extract_dir}")
                return 1

        print(f"Moving to {plugin_dest}...")
        shutil.move(str(extracted), str(plugin_dest))
        print("[OK] Plugin installed successfully!")

    except Exception as e:
        print(f"Error installing plugin: {e}")
        return 1

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return 0
