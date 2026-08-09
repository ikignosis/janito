"""Frontend wiring tests for the status-bar image-generation indicator.

The status bar shows an "image" flag badge that lights up when the next
prompt can generate images, mirroring the backend's gating:

* ``alibaba`` provider -- the ``CreateImage`` tool (Wan 2.7 Image Pro)
  loads whenever the active provider is alibaba
  (``janito.tools.janitoweb.create_image.CreateImage.should_load``);
* ``openai`` provider with the effective API type ``Responses`` -- the
  Responses runner appends the native ``image_generation`` tool
  (``janito.web.backend.agent.responses.build_call_kwargs``).

These tests pin down the frontend wiring (index.html badge + statusBar.js
computed getter) using static checks, like the thinking-toggle tests.
"""

from pathlib import Path

FRONTEND = Path(__file__).parent.parent.parent / "janito" / "web" / "frontend"


def test_index_html_has_image_badge_bound_to_image_gen():
    """The status bar shows an image badge whose active state follows imageGen."""
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert 'class="flag-badge" :class="{ active: imageGen }"' in html
    assert ">image</span>" in html


def test_status_bar_js_exposes_image_gen_getter():
    """statusBar.js resolves image generation from provider + API type."""
    js = (FRONTEND / "js" / "statusBar.js").read_text(encoding="utf-8")
    assert "get imageGen()" in js
    # The alibaba provider always has image generation (CreateImage tool).
    assert "provider === 'alibaba'" in js
    # openai only when the effective API type is the Responses API.
    assert "provider === 'openai'" in js
    assert "'responses'" in js
