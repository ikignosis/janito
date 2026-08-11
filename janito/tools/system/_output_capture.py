"""Shared output-capture helpers for the system exec tools.

Implements the "cap at 50 lines + keep a full-output temp file" behaviour
requested in issue #49: the tool result carries at most ``MAX_OUTPUT_LINES``
of stdout/stderr; when a stream is longer, a kept temporary file receives the
*complete* output (streamed in parallel to the screen) and the result points
at it, so the model never gets flooded with huge command output.

The temporary files are registered for removal when the janito process exits
(``atexit``), mirroring the pattern used by ``GetUrl`` / ``HeadlessBrowse``.
"""

import atexit
import os
import tempfile
from typing import Any

# Maximum number of output lines returned inline in the tool result dict.
# Anything beyond this is stored in a kept temp file and referenced by path.
MAX_OUTPUT_LINES = 50

_TEMP_FILES: set[str] = set()
_atexit_registered = False


def _cleanup_temp_files() -> None:
    """Remove all tracked temporary files (called on process exit)."""
    for path in list(_TEMP_FILES):
        try:
            os.remove(path)
        except OSError:
            pass
        _TEMP_FILES.discard(path)


def track_temp_file(path: str) -> None:
    """Register *path* for removal when the janito process exits."""
    global _atexit_registered
    if not path:
        return
    _TEMP_FILES.add(path)
    if not _atexit_registered:
        atexit.register(_cleanup_temp_files)
        _atexit_registered = True


def create_temp_file(stream_name: str) -> str:
    """Create a kept temp file for one output stream and return its path.

    The file is created with ``delete=False`` (kept) and registered with
    :func:`track_temp_file` so it is removed when the process exits.
    """
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        prefix=f"janito_{stream_name}_",
        encoding="utf-8",
        delete=False,
    )
    path = tmp.name
    tmp.close()
    track_temp_file(path)
    return path


def build_report_message(stdout_path: str | None, stderr_path: str | None) -> str:
    """Build the ``report_result`` tail per issue #49.

    e.g. ``"Full stdout stored at /tmp/..., stderr at /tmp/..."``.  Returns
    an empty string when neither stream overflowed.
    """
    if stdout_path and stderr_path:
        return f"Full stdout stored at {stdout_path}, stderr at {stderr_path}"
    if stdout_path:
        return f"Full stdout stored at {stdout_path}"
    if stderr_path:
        return f"Full stderr stored at {stderr_path}"
    return ""


def print_stored_files(result: dict[str, Any]) -> None:
    """Print the kept temp-file locations of a tool result, if any.

    Used by the CLI harnesses of the exec tools so users can find the full
    output that was capped in the result dict (issue #49).
    """
    if result.get("stdout_file"):
        print(f"  (full stdout: {result['stdout_file']})")
    if result.get("stderr_file"):
        print(f"  (full stderr: {result['stderr_file']})")


class OutputCapture:
    """Collect one output stream, capping the inline text at ``max_lines``.

    Each streamed display line is fed via :meth:`add` (from the streaming
    tee).  The first ``max_lines`` lines are kept in memory for the inline
    result; when the cap is exceeded, a kept temp file is created lazily and
    the *full* output -- including the lines that already streamed -- is
    written to it, so nothing is lost.

    Usage::

        cap = OutputCapture("stdout")
        cap.add(line)                # per streamed line (tee callback)
        text, path = cap.finalize()  # after the subprocess finishes

    ``path`` is ``None`` when the cap was never exceeded.
    """

    def __init__(self, stream_name: str, max_lines: int = MAX_OUTPUT_LINES):
        self.stream_name = stream_name
        self.max_lines = max_lines
        self._display_lines: list[str] = []
        self._file_path: str | None = None
        self._fh = None

    # -- lifecycle ------------------------------------------------------

    def add(self, line: str) -> None:
        """Feed one display line (without its trailing newline)."""
        self._display_lines.append(line)
        if self._file_path is not None:
            self._fh.write(line + "\n")
            self._fh.flush()
        elif len(self._display_lines) > self.max_lines:
            # First over-cap line: create the kept file and backfill every
            # line that already streamed (exactly ``max_lines`` of them).
            self._file_path = create_temp_file(self.stream_name)
            self._fh = open(self._file_path, "w", encoding="utf-8")
            for line in self._display_lines:
                self._fh.write(line + "\n")
            self._fh.flush()

    def finalize(self) -> tuple[str, str | None]:
        """Close the temp file and return ``(capped_text, file_path)``.

        ``capped_text`` holds at most ``max_lines`` lines; when the stream
        was longer it is followed by ``Full <stream> available at <path>``.
        ``file_path`` is ``None`` when the cap was never exceeded.
        """
        self._close()
        if self._file_path is None:
            return "\n".join(self._display_lines), None
        capped = "\n".join(self._display_lines[: self.max_lines])
        pointer = f"Full {self.stream_name} available at {self._file_path}"
        return f"{capped}\n{pointer}", self._file_path

    # -- accessors ------------------------------------------------------

    def line_count(self) -> int:
        """Number of lines seen so far (the full stream, not the cap)."""
        return len(self._display_lines)

    def preview(self, limit: int = 100) -> str:
        """First ``limit`` characters of the stream, newlines flattened."""
        text = "\n".join(self._display_lines)
        preview = text[:limit].replace("\n", " ")
        if len(text) > limit:
            preview += "..."
        return preview

    @property
    def file_path(self) -> str | None:
        """Path of the kept temp file, or None when the cap was not exceeded."""
        return self._file_path

    # -- internals ------------------------------------------------------

    def _close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None


__all__ = [
    "MAX_OUTPUT_LINES",
    "OutputCapture",
    "_cleanup_temp_files",
    "build_report_message",
    "create_temp_file",
    "print_stored_files",
    "track_temp_file",
]
