"""Helpers for the web UI contract tests.

The chat page (previously a single ~900-line ``janito/web/frontend/index.html``)
is now composed server-side from ``janito/web/backend/templates/base.html`` and
the partials under ``templates/partials/``.  ``render_index_html`` renders them
exactly like ``janito.web.backend.app.create_app`` does, so the static frontend
checks keep asserting against the fully composed page instead of individual
partial files.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from janito.web.backend.templating import make_environment  # noqa: E402


def render_index_html(auth_token=None) -> str:
    """Render the chat page (base.html + all partials) to a string."""
    return make_environment().get_template("base.html").render(auth_token=auth_token)
