"""
Chrome discovery and temp-file helpers for the HeadlessBrowse tool.

Extracted from :mod:`janito.tools.net.headless_browse`
these names) so the tool module stays focused on the ``HeadlessBrowse``
class and its CLI harness.
"""

import atexit
import os
import shutil

# Threshold (in characters) above which fetched content is written to a
# temporary file instead of being returned inline to the model. Rendering a
# page with a real browser tends to produce large DOM payloads, so we store
# them on disk and hand back a pointer instead (same behaviour as GetUrl).
BIG_CONTENT_THRESHOLD = 10_000

# Temporary files created by HeadlessBrowse for oversized content. They are
# removed automatically when the janito process exits.
_TEMP_FILES: set[str] = set()
_atexit_registered = False


def _cleanup_temp_files() -> None:
    """Remove all temporary files created by HeadlessBrowse (on exit)."""
    for path in list(_TEMP_FILES):
        try:
            os.remove(path)
        except OSError:
            pass
        _TEMP_FILES.discard(path)


def _track_temp_file(path: str) -> None:
    """Register a temporary file for removal on process exit."""
    global _atexit_registered
    if not path:
        return
    _TEMP_FILES.add(path)
    if not _atexit_registered:
        atexit.register(_cleanup_temp_files)
        _atexit_registered = True


# Candidate executable names (searched via PATH) and known absolute install
# paths for Chromium-based browsers on the supported platforms.
_BINARY_NAMES = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "chrome",
    "brave-browser",
    "microsoft-edge",
    "msedge",
)

_MACOS_APP_PATHS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
)


def _windows_chrome_candidates() -> list[str]:
    """Return the usual Windows install paths for Chrome and Edge."""
    candidates: list[str] = []
    program_files = os.environ.get("PROGRAMFILES", "")
    program_files_x86 = os.environ.get("PROGRAMFILES(X86)", "")
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    roots = [p for p in (program_files, program_files_x86, local_app_data) if p]
    for root in roots:
        candidates.append(
            os.path.join(root, "Google", "Chrome", "Application", "chrome.exe")
        )
        candidates.append(
            os.path.join(root, "Microsoft", "Edge", "Application", "msedge.exe")
        )
    return candidates


def _find_chrome() -> str | None:
    """Locate a Chrome/Chromium-based browser binary, or None if not found."""
    for name in _BINARY_NAMES:
        path = shutil.which(name)
        if path:
            return path
    for path in _MACOS_APP_PATHS + tuple(_windows_chrome_candidates()):
        if path and os.path.isfile(path):
            return path
    return None


def _truncate_content(
    content: str, max_length: int | None, max_lines: int | None
) -> str:
    """Apply the caller's length/line limits, appending truncation markers."""
    if max_length is not None and len(content) > max_length:
        content = content[:max_length] + "... [truncated]"
    if max_lines is not None:
        lines = content.split("\n")
        if len(lines) > max_lines:
            content = "\n".join(lines[:max_lines]) + "\n... [truncated]"
    return content
