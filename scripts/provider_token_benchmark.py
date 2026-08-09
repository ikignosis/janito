#!/usr/bin/env python3
"""Benchmark output-token usage across the configured janito providers.

For every provider that has an API key configured in the janito auth store
(``~/.janito/auth.json``, discovered via ``janito --list-keys``) this script
runs::

    janito -p <provider> -v --log=info "<prompt>"

extracts the output-token usage reported by each run and produces two files,
both saved to the system temp directory (e.g. ``/tmp`` on Linux) and kept
across runs, with their paths printed to the console:

* ``provider_tokens.json`` -- a per-provider usage report sorted by output
  tokens (highest first);
* ``provider_tokens.png``  -- a bar chart of output tokens per model, sorted
  the same way and rendered without any third-party dependency.

Token extraction
----------------
janito prints an ``=== Total: ... | In: ... | Out: ... ===`` summary line per
API round, and (with ``--log=info``) an exact ``Request completed: total=...
(in=..., out=..., ...)`` log line on stderr.  The exact log numbers are used
when available; the formatted ``Out:`` value (e.g. ``1.2k``) is the fallback.
When a prompt triggers several tool rounds the per-round counts are summed, so
``out_tokens`` is the total number of output tokens consumed by the whole
execution.

Usage::

    python scripts/provider_token_benchmark.py
    python scripts/provider_token_benchmark.py --prompt "Summarize the repo"
    python scripts/provider_token_benchmark.py --providers openai deepseek \
        --json /some/dir/report.json --png /some/dir/report.png

Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import struct
import subprocess
import sys
import tempfile
import zlib
from collections import Counter
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Embedded 8x8 monochrome bitmap font (public domain).
#
# Glyphs for ASCII 0x20-0x7E, indexed by ``ord(char) - 0x20``; each glyph is
# 8 rows of 8 bits (bit 7 = leftmost pixel).  Based on the classic VGA font
# by Marcel Sondaar / IBM, as published in the public-domain "font8x8" set
# by Daniel Hepper (https://github.com/dhepper/font8x8).
# ---------------------------------------------------------------------------
FONT8X8 = [
    # U+0020 ' '
    (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
    # U+0021 '!'
    (0x18, 0x3C, 0x3C, 0x18, 0x18, 0x00, 0x18, 0x00),
    # U+0022 '"'
    (0x36, 0x36, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
    # U+0023 '#'
    (0x36, 0x36, 0x7F, 0x36, 0x7F, 0x36, 0x36, 0x00),
    # U+0024 '$'
    (0x0C, 0x3E, 0x03, 0x1E, 0x30, 0x1F, 0x0C, 0x00),
    # U+0025 '%'
    (0x00, 0x63, 0x33, 0x18, 0x0C, 0x66, 0x63, 0x00),
    # U+0026 '&'
    (0x1C, 0x36, 0x1C, 0x6E, 0x3B, 0x33, 0x6E, 0x00),
    # U+0027 "'"
    (0x06, 0x06, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00),
    # U+0028 '('
    (0x18, 0x0C, 0x06, 0x06, 0x06, 0x0C, 0x18, 0x00),
    # U+0029 ')'
    (0x06, 0x0C, 0x18, 0x18, 0x18, 0x0C, 0x06, 0x00),
    # U+002A '*'
    (0x00, 0x66, 0x3C, 0xFF, 0x3C, 0x66, 0x00, 0x00),
    # U+002B '+'
    (0x00, 0x0C, 0x0C, 0x3F, 0x0C, 0x0C, 0x00, 0x00),
    # U+002C ','
    (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C, 0x06),
    # U+002D '-'
    (0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x00),
    # U+002E '.'
    (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C, 0x00),
    # U+002F '/'
    (0x60, 0x30, 0x18, 0x0C, 0x06, 0x03, 0x01, 0x00),
    # U+0030 '0'
    (0x3E, 0x63, 0x73, 0x7B, 0x6F, 0x67, 0x3E, 0x00),
    # U+0031 '1'
    (0x0C, 0x0E, 0x0C, 0x0C, 0x0C, 0x0C, 0x3F, 0x00),
    # U+0032 '2'
    (0x1E, 0x33, 0x30, 0x1C, 0x06, 0x33, 0x3F, 0x00),
    # U+0033 '3'
    (0x1E, 0x33, 0x30, 0x1C, 0x30, 0x33, 0x1E, 0x00),
    # U+0034 '4'
    (0x38, 0x3C, 0x36, 0x33, 0x7F, 0x30, 0x78, 0x00),
    # U+0035 '5'
    (0x3F, 0x03, 0x1F, 0x30, 0x30, 0x33, 0x1E, 0x00),
    # U+0036 '6'
    (0x1C, 0x06, 0x03, 0x1F, 0x33, 0x33, 0x1E, 0x00),
    # U+0037 '7'
    (0x3F, 0x33, 0x30, 0x18, 0x0C, 0x0C, 0x0C, 0x00),
    # U+0038 '8'
    (0x1E, 0x33, 0x33, 0x1E, 0x33, 0x33, 0x1E, 0x00),
    # U+0039 '9'
    (0x1E, 0x33, 0x33, 0x3E, 0x30, 0x18, 0x0E, 0x00),
    # U+003A ':'
    (0x00, 0x0C, 0x0C, 0x00, 0x00, 0x0C, 0x0C, 0x00),
    # U+003B ';'
    (0x00, 0x0C, 0x0C, 0x00, 0x00, 0x0C, 0x0C, 0x06),
    # U+003C '<'
    (0x18, 0x0C, 0x06, 0x03, 0x06, 0x0C, 0x18, 0x00),
    # U+003D '='
    (0x00, 0x00, 0x3F, 0x00, 0x00, 0x3F, 0x00, 0x00),
    # U+003E '>'
    (0x06, 0x0C, 0x18, 0x30, 0x18, 0x0C, 0x06, 0x00),
    # U+003F '?'
    (0x1E, 0x33, 0x30, 0x18, 0x0C, 0x00, 0x0C, 0x00),
    # U+0040 '@'
    (0x3E, 0x63, 0x7B, 0x7B, 0x7B, 0x03, 0x1E, 0x00),
    # U+0041 'A'
    (0x0C, 0x1E, 0x33, 0x33, 0x3F, 0x33, 0x33, 0x00),
    # U+0042 'B'
    (0x3F, 0x66, 0x66, 0x3E, 0x66, 0x66, 0x3F, 0x00),
    # U+0043 'C'
    (0x3C, 0x66, 0x03, 0x03, 0x03, 0x66, 0x3C, 0x00),
    # U+0044 'D'
    (0x1F, 0x36, 0x66, 0x66, 0x66, 0x36, 0x1F, 0x00),
    # U+0045 'E'
    (0x7F, 0x46, 0x16, 0x1E, 0x16, 0x46, 0x7F, 0x00),
    # U+0046 'F'
    (0x7F, 0x46, 0x16, 0x1E, 0x16, 0x06, 0x0F, 0x00),
    # U+0047 'G'
    (0x3C, 0x66, 0x03, 0x03, 0x73, 0x66, 0x7C, 0x00),
    # U+0048 'H'
    (0x33, 0x33, 0x33, 0x3F, 0x33, 0x33, 0x33, 0x00),
    # U+0049 'I'
    (0x1E, 0x0C, 0x0C, 0x0C, 0x0C, 0x0C, 0x1E, 0x00),
    # U+004A 'J'
    (0x78, 0x30, 0x30, 0x30, 0x33, 0x33, 0x1E, 0x00),
    # U+004B 'K'
    (0x67, 0x66, 0x36, 0x1E, 0x36, 0x66, 0x67, 0x00),
    # U+004C 'L'
    (0x0F, 0x06, 0x06, 0x06, 0x46, 0x66, 0x7F, 0x00),
    # U+004D 'M'
    (0x63, 0x77, 0x7F, 0x7F, 0x6B, 0x63, 0x63, 0x00),
    # U+004E 'N'
    (0x63, 0x67, 0x6F, 0x7B, 0x73, 0x63, 0x63, 0x00),
    # U+004F 'O'
    (0x1C, 0x36, 0x63, 0x63, 0x63, 0x36, 0x1C, 0x00),
    # U+0050 'P'
    (0x3F, 0x66, 0x66, 0x3E, 0x06, 0x06, 0x0F, 0x00),
    # U+0051 'Q'
    (0x1E, 0x33, 0x33, 0x33, 0x3B, 0x1E, 0x38, 0x00),
    # U+0052 'R'
    (0x3F, 0x66, 0x66, 0x3E, 0x36, 0x66, 0x67, 0x00),
    # U+0053 'S'
    (0x1E, 0x33, 0x07, 0x0E, 0x38, 0x33, 0x1E, 0x00),
    # U+0054 'T'
    (0x3F, 0x2D, 0x0C, 0x0C, 0x0C, 0x0C, 0x1E, 0x00),
    # U+0055 'U'
    (0x33, 0x33, 0x33, 0x33, 0x33, 0x33, 0x3F, 0x00),
    # U+0056 'V'
    (0x33, 0x33, 0x33, 0x33, 0x33, 0x1E, 0x0C, 0x00),
    # U+0057 'W'
    (0x63, 0x63, 0x63, 0x6B, 0x7F, 0x77, 0x63, 0x00),
    # U+0058 'X'
    (0x63, 0x63, 0x36, 0x1C, 0x1C, 0x36, 0x63, 0x00),
    # U+0059 'Y'
    (0x33, 0x33, 0x33, 0x1E, 0x0C, 0x0C, 0x1E, 0x00),
    # U+005A 'Z'
    (0x7F, 0x63, 0x31, 0x18, 0x4C, 0x66, 0x7F, 0x00),
    # U+005B '['
    (0x1E, 0x06, 0x06, 0x06, 0x06, 0x06, 0x1E, 0x00),
    # U+005C '\\'
    (0x03, 0x06, 0x0C, 0x18, 0x30, 0x60, 0x40, 0x00),
    # U+005D ']'
    (0x1E, 0x18, 0x18, 0x18, 0x18, 0x18, 0x1E, 0x00),
    # U+005E '^'
    (0x08, 0x1C, 0x36, 0x63, 0x00, 0x00, 0x00, 0x00),
    # U+005F '_'
    (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF),
    # U+0060 '`'
    (0x0C, 0x0C, 0x18, 0x00, 0x00, 0x00, 0x00, 0x00),
    # U+0061 'a'
    (0x00, 0x00, 0x1E, 0x30, 0x3E, 0x33, 0x6E, 0x00),
    # U+0062 'b'
    (0x07, 0x06, 0x06, 0x3E, 0x66, 0x66, 0x3B, 0x00),
    # U+0063 'c'
    (0x00, 0x00, 0x1E, 0x33, 0x03, 0x33, 0x1E, 0x00),
    # U+0064 'd'
    (0x38, 0x30, 0x30, 0x3E, 0x33, 0x33, 0x6E, 0x00),
    # U+0065 'e'
    (0x00, 0x00, 0x1E, 0x33, 0x3F, 0x03, 0x1E, 0x00),
    # U+0066 'f'
    (0x1C, 0x36, 0x06, 0x0F, 0x06, 0x06, 0x0F, 0x00),
    # U+0067 'g'
    (0x00, 0x00, 0x6E, 0x33, 0x33, 0x3E, 0x30, 0x1F),
    # U+0068 'h'
    (0x07, 0x06, 0x36, 0x6E, 0x66, 0x66, 0x67, 0x00),
    # U+0069 'i'
    (0x0C, 0x00, 0x0E, 0x0C, 0x0C, 0x0C, 0x1E, 0x00),
    # U+006A 'j'
    (0x30, 0x00, 0x30, 0x30, 0x30, 0x33, 0x33, 0x1E),
    # U+006B 'k'
    (0x07, 0x06, 0x66, 0x36, 0x1E, 0x36, 0x67, 0x00),
    # U+006C 'l'
    (0x0E, 0x0C, 0x0C, 0x0C, 0x0C, 0x0C, 0x1E, 0x00),
    # U+006D 'm'
    (0x00, 0x00, 0x33, 0x7F, 0x7F, 0x6B, 0x63, 0x00),
    # U+006E 'n'
    (0x00, 0x00, 0x1F, 0x33, 0x33, 0x33, 0x33, 0x00),
    # U+006F 'o'
    (0x00, 0x00, 0x1E, 0x33, 0x33, 0x33, 0x1E, 0x00),
    # U+0070 'p'
    (0x00, 0x00, 0x3B, 0x66, 0x66, 0x3E, 0x06, 0x0F),
    # U+0071 'q'
    (0x00, 0x00, 0x6E, 0x33, 0x33, 0x3E, 0x30, 0x78),
    # U+0072 'r'
    (0x00, 0x00, 0x3B, 0x6E, 0x66, 0x06, 0x0F, 0x00),
    # U+0073 's'
    (0x00, 0x00, 0x3E, 0x03, 0x1E, 0x30, 0x1F, 0x00),
    # U+0074 't'
    (0x08, 0x0C, 0x3E, 0x0C, 0x0C, 0x2C, 0x18, 0x00),
    # U+0075 'u'
    (0x00, 0x00, 0x33, 0x33, 0x33, 0x33, 0x6E, 0x00),
    # U+0076 'v'
    (0x00, 0x00, 0x33, 0x33, 0x33, 0x1E, 0x0C, 0x00),
    # U+0077 'w'
    (0x00, 0x00, 0x63, 0x6B, 0x7F, 0x7F, 0x36, 0x00),
    # U+0078 'x'
    (0x00, 0x00, 0x63, 0x36, 0x1C, 0x36, 0x63, 0x00),
    # U+0079 'y'
    (0x00, 0x00, 0x33, 0x33, 0x33, 0x3E, 0x30, 0x1F),
    # U+007A 'z'
    (0x00, 0x00, 0x3F, 0x19, 0x0C, 0x26, 0x3F, 0x00),
    # U+007B '{'
    (0x38, 0x0C, 0x0C, 0x07, 0x0C, 0x0C, 0x38, 0x00),
    # U+007C '|'
    (0x18, 0x18, 0x18, 0x00, 0x18, 0x18, 0x18, 0x00),
    # U+007D '}'
    (0x07, 0x0C, 0x0C, 0x38, 0x0C, 0x0C, 0x07, 0x00),
    # U+007E '~'
    (0x6E, 0x3B, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
]

# Distinct, white-background-friendly bar colors (Material 500-ish palette).
PALETTE = [
    (0xE5, 0x39, 0x35),  # red
    (0x1E, 0x88, 0xE5),  # blue
    (0xFB, 0x8C, 0x00),  # orange
    (0x43, 0xA0, 0x47),  # green
    (0x00, 0xAC, 0xC1),  # cyan
    (0x8E, 0x24, 0xAA),  # purple
    (0xD8, 0x1B, 0x60),  # pink
    (0x6D, 0x4C, 0x41),  # brown
    (0x39, 0x49, 0xAB),  # indigo
    (0xF0, 0x62, 0x92),  # light pink
]

WHITE = (0xFF, 0xFF, 0xFF)
INK = (0x21, 0x21, 0x21)  # dark gray text
MUTED = (0x75, 0x75, 0x75)  # subtitle / secondary text
GRID = (0xE0, 0xE0, 0xE0)  # grid lines
AXIS = (0x9E, 0x9E, 0x9E)  # axis line

# Bar-chart layout (module-level so callers/tests can reason about the canvas).
CHAR_SCALE = 2
CHAR_SPACING = 1
TITLE_SCALE = 3
BAR_H = 24
ROW_GAP = 14
ROW_H = BAR_H + ROW_GAP
CHART_W = 520
MARGIN_L = 20
MARGIN_R = 20
MARGIN_T = 96
MARGIN_B = 80

# ---------------------------------------------------------------------------
# janito output parsing
# ---------------------------------------------------------------------------

MODEL_RE = re.compile(
    r"^----- Model:\s*(.+?)\s*\|\s*Backend:\s*(.*?)\s*$", re.MULTILINE
)

# Exact per-round usage from the --log=info line emitted by
# janito.openai_client.client_support._display_usage, e.g.:
#   INFO: Request completed: total=1234 tokens (in=1000, out=234, cached=None, max=128000), 1 messages
USAGE_LOG_RE = re.compile(
    r"INFO: Request completed: total=(?P<total>\d+|None) tokens "
    r"\(in=(?P<in>\d+|None), out=(?P<out>\d+|None), "
    r"cached=(?P<cached>\d+|None), max=(?P<max>\d+|None)\), "
    r"(?P<count>\d+) (?:messages|responses)"
)

# The human-readable summary line, e.g.:
#   === Total: 1.2k | In: 1k | Out: 234 | Messages: 1 ===
SUMMARY_LINE_RE = re.compile(r"^=== .* ===\s*$", re.MULTILINE)
OUT_PART_RE = re.compile(
    r"Out:\s*([0-9]+(?:\.[0-9]+)?[km]?)(?:\s*/\s*[0-9]+(?:\.[0-9]+)?[km]?)?"
)

# Provider lines from `janito --list-keys`, e.g. "  openai: ***".
LIST_KEYS_PROVIDER_RE = re.compile(r"^\s{2}([^\s:]+):\s*\*+\s*$", re.MULTILINE)

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def format_tokens(count: int | None) -> str | None:
    """Human-readable token count, mirroring janito's ``format_tokens``."""
    if count is None:
        return None
    try:
        value = float(count)
    except (TypeError, ValueError):
        return str(count)

    def _fmt(number: float) -> str:
        return str(int(number)) if number == int(number) else f"{number:.1f}"

    if value >= 1_000_000:
        return f"{_fmt(value / 1_000_000)}m"
    if value >= 1_000:
        return f"{_fmt(value / 1_000)}k"
    return str(int(value))


_TOKEN_SUFFIX = {"": 1, "k": 1_000, "m": 1_000_000}


def unformat_tokens(value: str | None) -> int | None:
    """Convert a formatted token value (``"150"``, ``"1.2k"``, ``"4m"``) to int."""
    if value is None:
        return None
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([km]?)", value.strip())
    if not match:
        return None
    return int(float(match.group(1)) * _TOKEN_SUFFIX[match.group(2)])


def parse_model(stdout: str) -> str | None:
    """Extract the model name from the ``-v`` banner (``----- Model: ... | ...``)."""
    match = MODEL_RE.search(stdout)
    return match.group(1).strip() if match else None


def parse_usage_log(stderr: str) -> list[dict]:
    """Extract exact per-round usage dicts from the ``--log=info`` lines."""
    rounds: list[dict] = []
    for match in USAGE_LOG_RE.finditer(stderr):
        values = {
            name: match.group(name) for name in ("total", "in", "out", "cached", "max")
        }
        rounds.append(
            {
                "total": int(values["total"]) if values["total"] != "None" else None,
                "in": int(values["in"]) if values["in"] != "None" else None,
                "out": int(values["out"]) if values["out"] != "None" else None,
                "cached": int(values["cached"]) if values["cached"] != "None" else None,
                "max": int(values["max"]) if values["max"] != "None" else None,
                "count": int(match.group("count")),
            }
        )
    return rounds


def parse_usage_summary(stdout: str) -> list[str]:
    """Extract the formatted ``Out:`` values from the ``=== ... ===`` summary lines."""
    values: list[str] = []
    for line in SUMMARY_LINE_RE.findall(stdout):
        match = OUT_PART_RE.search(line)
        if match:
            values.append(match.group(1))
    return values


_LOG_NOISE_RE = re.compile(r"^(INFO|DEBUG|WARNING|CRITICAL):", re.IGNORECASE)
_ERROR_HINT_RE = re.compile(
    r"error|exception|traceback|failed|missing|cannot|can't|not installed|unknown|requires",
    re.IGNORECASE,
)


def _first_error(stdout: str, stderr: str) -> str | None:
    """Pick the most useful error line from the captured output.

    Log-noise lines (``INFO:``/``DEBUG:``/...) are skipped; the root cause of
    a traceback is usually its final line, so the last error-looking line wins.
    """
    for text in (stderr, stdout):
        lines = [ANSI_ESCAPE_RE.sub("", line).strip() for line in text.splitlines()]
        meaningful = [line for line in lines if line and not _LOG_NOISE_RE.match(line)]
        if not meaningful:
            continue
        hints = [line for line in meaningful if _ERROR_HINT_RE.search(line)]
        if hints:
            return hints[-1][:300]
        return meaningful[-1][:300]
    return None


def build_result(provider: str, returncode: int, stdout: str, stderr: str) -> dict:
    """Build one JSON record from a janito subprocess run."""
    entry: dict = {
        "provider": provider,
        "model": parse_model(stdout),
        "status": "ok",
        "out_tokens": None,
        "in_tokens": None,
        "total_tokens": None,
        "out_display": None,
        "out_tokens_source": None,
        "rounds": 0,
        "error": None,
    }
    if returncode != 0:
        entry["status"] = "error"
        entry["error"] = (
            _first_error(stdout, stderr) or f"janito exited with code {returncode}"
        )
        return entry

    log_rounds = parse_usage_log(stderr)
    if log_rounds:
        entry["out_tokens"] = sum(r["out"] for r in log_rounds if r["out"] is not None)
        entry["in_tokens"] = sum(r["in"] for r in log_rounds if r["in"] is not None)
        entry["total_tokens"] = sum(
            r["total"] for r in log_rounds if r["total"] is not None
        )
        entry["rounds"] = len(log_rounds)
        entry["out_tokens_source"] = "log"
    else:
        out_parts = [unformat_tokens(value) for value in parse_usage_summary(stdout)]
        out_parts = [value for value in out_parts if value is not None]
        if out_parts:
            entry["out_tokens"] = sum(out_parts)
            entry["rounds"] = len(out_parts)
            entry["out_tokens_source"] = "display"
        else:
            entry["status"] = "no-usage"
            entry["error"] = "no token usage found in janito output"

    entry["out_display"] = format_tokens(entry["out_tokens"])
    return entry


def parse_list_keys(output: str) -> list[str]:
    """Extract provider names from ``janito --list-keys`` output."""
    return sorted({match.group(1) for match in LIST_KEYS_PROVIDER_RE.finditer(output)})


def discover_providers(janito_cmd: str, timeout: int = 60) -> list[str]:
    """Return the providers that have an API key configured (auth.json)."""
    proc = subprocess.run(
        [janito_cmd, "--list-keys"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"`{janito_cmd} --list-keys` failed (exit {proc.returncode}): "
            f"{_first_error(proc.stdout, proc.stderr)}"
        )
    return parse_list_keys(proc.stdout)


def run_janito(
    janito_cmd: str, provider: str, prompt: str, timeout: int
) -> subprocess.CompletedProcess:
    """Run janito for one provider.

    The prompt is passed both as the CLI argument and piped through stdin:
    janito reads all of stdin when it is not a TTY, so feeding the prompt on
    stdin avoids the "Empty prompt provided via stdin" error and guarantees a
    single-prompt run even in a fully non-interactive context.
    """
    cmd = [janito_cmd, "-p", provider, "-v", "--log=info", prompt]
    return subprocess.run(
        cmd,
        input=prompt + "\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def sort_results(results: list[dict]) -> list[dict]:
    """Successful runs first (by out_tokens desc), failures last (by provider)."""
    ok = [r for r in results if r["out_tokens"] is not None]
    failed = [r for r in results if r["out_tokens"] is None]
    ok.sort(key=lambda r: r["out_tokens"], reverse=True)
    failed.sort(key=lambda r: r["provider"])
    return ok + failed


def write_json(results: list[dict], path: Path, prompt: str, janito_cmd: str) -> None:
    """Write the JSON report (sorted by out_tokens, highest first)."""
    data = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "prompt": prompt,
        "janito_command": janito_cmd,
        "results": results,
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def chart_entries(results: list[dict]) -> list[tuple[str, int]]:
    """Build ``(label, out_tokens)`` pairs, sorted by tokens descending.

    Labels are model names; when two providers resolve to the same model the
    provider is appended for disambiguation.
    """
    ok = [r for r in results if r["out_tokens"] is not None]
    ok.sort(key=lambda r: r["out_tokens"], reverse=True)
    counts = Counter(r["model"] for r in ok if r["model"])
    entries: list[tuple[str, int]] = []
    for r in ok:
        label = r["model"] or r["provider"]
        if r["model"] and counts[r["model"]] > 1:
            label = f"{r['model']} ({r['provider']})"
        entries.append((label, int(r["out_tokens"])))
    return entries


def resolve_artifact_path(explicit: str | None, filename: str) -> Path:
    """Resolve an output artifact path.

    An explicit path (``--json`` / ``--png``) always wins; otherwise the
    artifact is saved to the system temp directory (``tempfile.gettempdir()``,
    e.g. ``/tmp`` on Linux) so it is kept across runs.

    Args:
        explicit: The CLI argument value (``None`` when not given).
        filename: The default file name (e.g. ``"provider_tokens.png"``).

    Returns:
        The resolved output path for the artifact.
    """
    if explicit:
        return Path(explicit)
    return Path(tempfile.gettempdir()) / filename


# ---------------------------------------------------------------------------
# Dependency-free PNG bar chart
# ---------------------------------------------------------------------------


class Canvas:
    """Minimal RGB canvas with fill/text helpers."""

    def __init__(self, width: int, height: int, background: tuple = WHITE):
        self.width = width
        self.height = height
        self._background = background
        self.pixels = [[background] * width for _ in range(height)]

    def fill_rect(self, x0: int, y0: int, x1: int, y1: int, color: tuple) -> None:
        """Fill the inclusive rectangle (x0, y0) .. (x1, y1)."""
        x0, x1 = max(0, x0), min(self.width - 1, x1)
        y0, y1 = max(0, y0), min(self.height - 1, y1)
        if x0 > x1 or y0 > y1:
            return
        for y in range(y0, y1 + 1):
            row = self.pixels[y]
            for x in range(x0, x1 + 1):
                row[x] = color

    def text(
        self, x: int, y: int, text: str, color: tuple, scale: int = 2, spacing: int = 1
    ) -> int:
        """Draw text with the embedded 8x8 font; returns the end x coordinate."""
        for char in text:
            code = ord(char)
            rows = FONT8X8[code - 0x20] if 0x20 <= code <= 0x7E else FONT8X8[0]
            for row_index, row in enumerate(rows):
                for col in range(8):
                    # FONT8X8 stores the leftmost pixel in the least
                    # significant bit.  Reading it MSB-first mirrors every
                    # label and makes the chart text appear right-to-left.
                    if row & (1 << col):
                        px, py = x + col * scale, y + row_index * scale
                        self.fill_rect(px, py, px + scale - 1, py + scale - 1, color)
            x += 8 * scale + spacing
        return x - spacing


def text_width(text: str, scale: int = 2, spacing: int = 1) -> int:
    """Width of ``text`` when drawn with :meth:`Canvas.text`."""
    if not text:
        return 0
    return len(text) * (8 * scale + spacing) - spacing


def _darken(color: tuple, factor: float = 0.7) -> tuple:
    return tuple(max(0, int(channel * factor)) for channel in color)


def _nice_max(value: int) -> int:
    """Round ``value`` up to a "nice" number (1/2/5 x 10^n)."""
    if value <= 0:
        return 1
    exponent = 10 ** math.floor(math.log10(value))
    for multiplier in (1, 2, 5, 10):
        if value <= multiplier * exponent:
            return multiplier * exponent
    return 10 * exponent


def _truncate(text: str, width: int, scale: int = 2, spacing: int = 1) -> str:
    if text_width(text, scale, spacing) <= width:
        return text
    ellipsis = "..."
    while text and text_width(text + ellipsis, scale, spacing) > width:
        text = text[:-1]
    return text + ellipsis


def render_chart(
    entries: list[tuple[str, int]], out_path: Path, prompt: str, generated_at: str
) -> None:
    """Render a horizontal bar chart of output tokens per model as a PNG."""
    if not entries:
        raise ValueError("render_chart() requires at least one entry")

    scale = CHAR_SCALE
    spacing = CHAR_SPACING
    label_w = max(
        110, max(text_width(label, scale, spacing) for label, _ in entries) + 16
    )
    value_w = max(
        56,
        max(
            text_width(format_tokens(value) or "0", scale, spacing)
            for _, value in entries
        )
        + 16,
    )
    chart_x0 = MARGIN_L + label_w + 16
    value_x0 = chart_x0 + CHART_W + 10

    width = MARGIN_L + label_w + 16 + CHART_W + 10 + value_w + MARGIN_R
    height = MARGIN_T + len(entries) * ROW_H + MARGIN_B
    canvas = Canvas(width, height)

    # Title + subtitle
    canvas.text(
        MARGIN_L, 26, "Output tokens per model", INK, scale=TITLE_SCALE, spacing=2
    )
    subtitle = _truncate(
        f'Prompt: "{prompt}"  |  {generated_at}',
        width - MARGIN_L - MARGIN_R,
        scale,
        spacing,
    )
    canvas.text(MARGIN_L, 68, subtitle, MUTED, scale=scale, spacing=spacing)

    max_value = max(value for _, value in entries)
    nice_max = _nice_max(max_value)
    divisions = 5
    step = nice_max / divisions

    plot_top = MARGIN_T
    plot_bottom = MARGIN_T + len(entries) * ROW_H - ROW_GAP

    # Vertical grid lines + labels
    for i in range(divisions + 1):
        x = chart_x0 + round(CHART_W * i / divisions)
        canvas.fill_rect(x, plot_top, x, plot_bottom, GRID)
        label = format_tokens(round(step * i)) or "0"
        canvas.text(
            x - text_width(label, scale, spacing) // 2,
            plot_bottom + 14,
            label,
            MUTED,
            scale,
            spacing,
        )

    # Axis line
    canvas.fill_rect(chart_x0, plot_bottom, chart_x0 + CHART_W, plot_bottom + 1, AXIS)

    # Bars grow from the zero axis towards increasing values (left to right).
    # Keep the zero point as the left edge explicitly: using ``CHART_W -
    # bar_w`` here would mirror the chart and make the visualisation read
    # right-to-left.
    for index, (label, value) in enumerate(entries):
        row_y = MARGIN_T + index * ROW_H
        color = PALETTE[index % len(PALETTE)]
        bar_w = round(CHART_W * value / nice_max)
        bar_w = max(bar_w, 1) if value > 0 else 0
        bar_x0 = chart_x0
        bar_x1 = bar_x0 + bar_w - 1
        canvas.fill_rect(bar_x0, row_y, bar_x1, row_y + BAR_H - 1, color)
        # 1px darker outline for definition
        outline = _darken(color, 0.7)
        canvas.fill_rect(bar_x0, row_y, bar_x1, row_y, outline)
        canvas.fill_rect(bar_x0, row_y + BAR_H - 1, bar_x1, row_y + BAR_H - 1, outline)
        canvas.fill_rect(bar_x0, row_y, bar_x0, row_y + BAR_H - 1, outline)

        text_y = row_y + (BAR_H - 8 * scale) // 2
        canvas.text(MARGIN_L, text_y, label, INK, scale, spacing)
        canvas.text(value_x0, text_y, format_tokens(value) or "0", INK, scale, spacing)

    out_path.write_bytes(encode_png(canvas))


def encode_png(canvas: Canvas) -> bytes:
    """Encode a :class:`Canvas` as a PNG (8-bit RGB, no dependencies)."""
    width, height = canvas.width, canvas.height
    raw = bytearray()
    for row in canvas.pixels:
        raw.append(0)  # filter: None
        for red, green, blue in row:
            raw += bytes((red, green, blue))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="provider_token_benchmark",
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Artifacts: provider_tokens.json (report) and provider_tokens.png "
        "(bar chart), both saved to the system temp dir and kept across runs, "
        "with their paths printed.",
    )
    parser.add_argument(
        "--prompt",
        default="What is this project about",
        help="Prompt sent to every provider (default: %(default)r)",
    )
    parser.add_argument(
        "--providers",
        nargs="*",
        default=None,
        help="Providers to benchmark; defaults to every provider with a configured API key",
    )
    parser.add_argument(
        "--janito",
        default="janito",
        help="janito executable (default: %(default)r)",
    )
    parser.add_argument(
        "--json",
        default=None,
        help="output JSON report path (default: <tmp>/provider_tokens.json)",
    )
    parser.add_argument(
        "--png",
        default=None,
        help="output PNG chart path (default: <tmp>/provider_tokens.png)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=900,
        help="per-provider timeout in seconds (default: %(default)s)",
    )
    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="print the providers with a configured API key and exit",
    )
    args = parser.parse_args(argv)

    if args.list_providers:
        try:
            providers = discover_providers(args.janito)
        except (subprocess.TimeoutExpired, RuntimeError, OSError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        for provider in providers:
            print(provider)
        return 0

    try:
        providers = args.providers or discover_providers(args.janito)
    except (subprocess.TimeoutExpired, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not providers:
        print(
            "Error: no providers with a configured API key found; "
            "use --providers to pick some explicitly.",
            file=sys.stderr,
        )
        return 1

    results: list[dict] = []
    for provider in providers:
        print(f"Running janito -p {provider} ...", file=sys.stderr)
        try:
            proc = run_janito(args.janito, provider, args.prompt, args.timeout)
        except subprocess.TimeoutExpired:
            entry: dict = {
                "provider": provider,
                "model": None,
                "status": "error",
                "out_tokens": None,
                "in_tokens": None,
                "total_tokens": None,
                "out_display": None,
                "out_tokens_source": None,
                "rounds": 0,
                "error": f"timed out after {args.timeout}s",
            }
            results.append(entry)
            continue
        results.append(
            build_result(provider, proc.returncode, proc.stdout, proc.stderr)
        )

    results = sort_results(results)
    json_path = resolve_artifact_path(args.json, "provider_tokens.json")
    write_json(results, json_path, args.prompt, args.janito)
    print(f"Wrote {json_path}")

    entries = chart_entries(results)
    if entries:
        generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
        png_path = resolve_artifact_path(args.png, "provider_tokens.png")
        render_chart(entries, png_path, args.prompt, generated_at)
        print(f"Wrote {png_path}")
    else:
        print("Skipping chart: no successful runs with token usage.", file=sys.stderr)

    # Human-readable summary
    print()
    header = f"{'provider':<16} {'model':<28} {'out':>8}  status"
    print(header)
    print("-" * len(header))
    for result in results:
        print(
            f"{result['provider']:<16} "
            f"{(result['model'] or '-'):<28} "
            f"{(result['out_display'] or '-'):>8}  "
            f"{result['status']}"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)
