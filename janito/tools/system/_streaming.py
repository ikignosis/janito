"""Shared subprocess streaming-execution helper for the system tools."""

import queue
import subprocess
import threading
import time
from collections.abc import Callable
from typing import Any


def stream_execute(
    command: list[str] | str,
    working_dir: str,
    capture_output: bool,
    capture_errors: bool,
    timeout: int | None,
    start_time: float,
    report_output: Callable[[str], None],
    *,
    report_blank_first: bool = False,
    popen_kwargs: dict[str, Any] | None = None,
    tee: Callable[[str, str], None] | None = None,
) -> tuple[int, list[str], list[str], int]:
    """Run ``command`` with real-time output streaming.

    Args:
        command: The argv list (or shell string) to execute.
        working_dir: Directory the subprocess runs in.
        capture_output: Capture stdout lines (else stdout is DEVNULL).
        capture_errors: Capture stderr lines (else stderr is DEVNULL).
        timeout: Kill the process after this many seconds (None = no limit).
        start_time: ``time.time()`` captured by the caller, used to compute
            the execution duration.
        report_output: Callback receiving each output line as it is produced.
        report_blank_first: When True, emit an empty line before the first
            output line (matches the shell tools' behaviour).
        popen_kwargs: Extra keyword arguments forwarded to
            :class:`subprocess.Popen` (e.g. ``encoding``, ``env``).
        tee: Optional ``(stream_name, line)`` callback invoked for every
            real stdout/stderr line as it is delivered to ``report_output``
            (in parallel to the screen).  ``line`` has no trailing newline;
            ``stream_name`` is ``"stdout"`` or ``"stderr"``.  Used by the
            exec tools to mirror the full output to a temp file while the
            inline result is capped (issue #49).

    Returns:
        ``(exit_code, captured_stdout, captured_stderr, execution_time_ms)``.
        ``exit_code`` is ``-1`` when the process was killed by a timeout.
    """
    captured_stdout: list[str] = []
    captured_stderr: list[str] = []

    process, output_queue = _launch(
        command, working_dir, capture_output, capture_errors, popen_kwargs
    )
    threads = _start_reader_threads(
        process,
        output_queue,
        capture_output,
        capture_errors,
        captured_stdout,
        captured_stderr,
    )
    exit_code, displayed_any_output = _monitor(
        process,
        output_queue,
        timeout,
        start_time,
        report_output,
        report_blank_first,
        tee,
    )

    for t in threads:
        t.join(timeout=1)

    _drain(
        output_queue,
        displayed_any_output,
        report_output,
        report_blank_first=report_blank_first,
        report_stream_errors=False,
        tee=tee,
    )

    execution_time_ms = int((time.time() - start_time) * 1000)
    return exit_code, captured_stdout, captured_stderr, execution_time_ms


def _launch(
    command: list[str] | str,
    working_dir: str,
    capture_output: bool,
    capture_errors: bool,
    popen_kwargs: dict[str, Any] | None,
) -> tuple[subprocess.Popen, queue.Queue[tuple[str, str]]]:
    """Start the subprocess and return ``(process, output_queue)``."""
    popen_options: dict[str, Any] = {
        "cwd": working_dir,
        "stdout": subprocess.PIPE if capture_output else subprocess.DEVNULL,
        "stderr": subprocess.PIPE if capture_errors else subprocess.DEVNULL,
        "text": True,
        "shell": False,
        "bufsize": 1,
        "universal_newlines": True,
    }
    if popen_kwargs:
        popen_options.update(popen_kwargs)
    process = subprocess.Popen(command, **popen_options)
    return process, queue.Queue()


def _start_reader_threads(
    process: subprocess.Popen,
    output_queue: queue.Queue[tuple[str, str]],
    capture_output: bool,
    capture_errors: bool,
    captured_stdout: list[str],
    captured_stderr: list[str],
) -> list[threading.Thread]:
    """Start reader threads for the captured streams."""
    threads: list[threading.Thread] = []
    if capture_output and process.stdout:
        threads.append(
            _start_reader_thread(
                output_queue, process.stdout, "stdout", captured_stdout
            )
        )
    if capture_errors and process.stderr:
        threads.append(
            _start_reader_thread(
                output_queue, process.stderr, "stderr", captured_stderr
            )
        )
    return threads


def _start_reader_thread(
    output_queue: queue.Queue[tuple[str, str]],
    stream: Any,
    stream_name: str,
    capture_list: list[str],
) -> threading.Thread:
    """Create and start a single reader thread."""
    t = threading.Thread(
        target=_read_stream,
        args=(output_queue, stream, stream_name, capture_list),
        daemon=True,
    )
    t.start()
    return t


def _read_stream(
    output_queue: queue.Queue[tuple[str, str]],
    stream: Any,
    stream_name: str,
    capture_list: list[str] | None,
) -> None:
    """Read lines from *stream* and enqueue them."""
    try:
        for line in iter(stream.readline, ""):
            if line:
                output_queue.put((stream_name, line.rstrip("\r\n")))
                if capture_list is not None:
                    capture_list.append(line)
        stream.close()
    except Exception as e:  # noqa: BLE001 - reader must never crash the loop
        output_queue.put(("error", f"Error reading {stream_name}: {e}"))


def _monitor(
    process: subprocess.Popen,
    output_queue: queue.Queue[tuple[str, str]],
    timeout: int | None,
    start_time: float,
    report_output: Callable[[str], None],
    report_blank_first: bool,
    tee: Callable[[str, str], None] | None = None,
) -> tuple[int, bool]:
    """Poll the process, streaming output, until it exits or times out."""
    exit_code: int | None = None
    displayed_any_output = False
    start_display_time = time.time()

    while True:
        exit_code = process.poll()
        process_finished = exit_code is not None
        displayed_any_output = _drain(
            output_queue,
            displayed_any_output,
            report_output,
            report_blank_first=report_blank_first,
            report_stream_errors=True,
            tee=tee,
        )
        if process_finished:
            break
        if timeout is not None:
            elapsed = time.time() - start_display_time
            if elapsed > timeout:
                process.kill()
                exit_code = -1
                break
        time.sleep(0.01)

    return exit_code, displayed_any_output


def _drain(
    output_queue: queue.Queue[tuple[str, str]],
    displayed_any_output: bool,
    report_output: Callable[[str], None],
    *,
    report_blank_first: bool,
    report_stream_errors: bool,
    tee: Callable[[str, str], None] | None = None,
) -> bool:
    """Deliver all queued lines to ``report_output``; return the new flag value."""
    try:
        while True:
            stream_name, line = output_queue.get_nowait()
            if stream_name in ("stdout", "stderr"):
                if not displayed_any_output:
                    if report_blank_first:
                        report_output("")
                    displayed_any_output = True
                report_output(line)
                if tee is not None:
                    tee(stream_name, line)
            elif report_stream_errors and stream_name == "error":
                report_output(f"STREAM ERROR: {line}")
    except queue.Empty:
        pass
    return displayed_any_output
