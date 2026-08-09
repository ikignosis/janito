"""Jinja2 environment for the web UI page templates.

The chat page (previously a single ~900-line ``frontend/index.html``) is
composed server-side from ``templates/base.html`` plus the partials under
``templates/partials/``.  This module owns the environment so the backend
(``app.py``) and the contract tests (``tests/web/_frontend.py``) render
through exactly the same setup (loader, autoescaping, whitespace control).
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATES_DIR = Path(__file__).parent / "templates"


def make_environment() -> Environment:
    """Build the Jinja2 environment used to render the web UI templates.

    ``lstrip_blocks``/``trim_blocks`` keep the composed page byte-identical to
    a hand-written shell: leading whitespace before an ``{% include %}`` tag
    and the tag's own newline are removed, so partials are spliced in without
    shifting indentation or injecting blank lines.
    """
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(("html", "xml")),
        lstrip_blocks=True,
        trim_blocks=True,
    )
