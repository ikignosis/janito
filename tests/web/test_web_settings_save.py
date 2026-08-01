"""Frontend wiring tests for the Settings drawer Save button (issue #38).

The Settings drawer's Save button must start disabled and only become
enabled when the drawer actually holds unsaved changes: the model field
differs from the value it loaded with, a different provider was staged as
the default via "Set Default", or an API key was staged via "Set API Key".

"Set Default" and "Set API Key" never write to disk the moment they are
clicked — they only arm the Save button (the changes are staged in the
component).  A successful save applies every staged change (default
provider, model, API key) and re-baselines the drawer, disabling Save
again.

These are static contract checks on the frontend sources (same pattern as
the other ``tests/web/test_web_*.py`` modules): they pin the Alpine
component state/computed properties and the ``:disabled`` binding so the
behaviour cannot regress silently.
"""

from pathlib import Path

FRONTEND = Path(__file__).parent.parent.parent / "janito" / "web" / "frontend"


def _settings_js():
    return (FRONTEND / "js" / "settings.js").read_text(encoding="utf-8")


def test_settings_tracks_pristine_baseline():
    """The component records what it loaded so it can detect edits."""
    js = _settings_js()
    # State that captures the pristine baseline (issue #38).
    assert "originalModel" in js
    assert "defaultChanged" in js
    # Staged (unsaved) changes for Set Default / Set API Key.
    assert "pendingDefaultProvider" in js
    assert "pendingApiKey" in js
    # The baseline is (re)established every time the drawer loads.
    assert "this.originalModel = this.model;" in js
    assert "this.defaultChanged = false;" in js


def test_can_save_combines_all_dirty_sources():
    """Save is enabled when the model differs, a default is staged, or an
    API key is staged; otherwise it stays disabled."""
    js = _settings_js()
    assert "get canSave()" in js
    assert "this.model !== this.originalModel" in js
    assert "this.defaultChanged" in js
    assert "apiKeyChanged" in js


def test_set_default_stages_instead_of_persisting():
    """Promoting a provider to the default marks the drawer dirty but does
    NOT call the backend yet — only Save persists it."""
    js = _settings_js()
    # The staged provider's model is mirrored into the field (keeps the
    # drawer in sync with what the next prompt would use once saved)...
    assert "this.model = p.model || this.model;" in js
    # ...and the drawer is flagged as holding unsaved changes.
    assert "this.defaultChanged = true;" in js
    # No immediate persistence: the endpoint is only reached from save().
    assert "Api.setDefaultProvider(this.pendingDefaultProvider)" in js


def test_save_api_key_stages_instead_of_persisting():
    """Set API Key stores the key in the drawer and arms Save; it is not
    written to auth.json until Save is clicked."""
    js = _settings_js()
    assert "this.pendingApiKey = { provider: this.selectedProvider, key };" in js
    assert "Api.setApiKey(this.pendingApiKey.provider, this.pendingApiKey.key)" in js


def test_save_applies_all_staged_changes():
    """A successful save persists the default, the model and the key."""
    js = _settings_js()
    assert "await Api.setDefaultProvider(this.pendingDefaultProvider);" in js
    assert "await Api.patchConfig({ model: this.model });" in js
    assert (
        "await Api.setApiKey(this.pendingApiKey.provider, this.pendingApiKey.key);"
        in js
    )


def test_save_restores_pristine_state():
    """A successful save re-baselines the drawer, disabling Save again."""
    js = _settings_js()
    assert "this.originalModel = this.model;" in js
    assert "this.defaultChanged = false;" in js
    assert "this.pendingDefaultProvider = null;" in js
    assert "this.pendingApiKey = null;" in js


def test_index_html_disables_save_until_dirty():
    """The Save button is bound to the canSave computed property."""
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert ':disabled="saving || !canSave"' in html


def test_model_field_placeholder_shows_default_model():
    """The Model field placeholder names the default model with a
    \"(default)\" marker instead of the old \"(not set)\"."""
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert 'x-model="model" :placeholder="modelPlaceholder"' in html
    assert 'placeholder="(not set)"' not in html


def test_settings_js_exposes_default_model_placeholder():
    """The drawer computes the default model (per-provider override, then
    built-in default) and renders \"(default)\" when no override is set."""
    js = _settings_js()
    # Resolution mirrors the provider switcher: configured model first,
    # falling back to the provider's built-in default.
    assert "get defaultModel()" in js
    assert "p.model || p.default_model" in js
    # The placeholder keeps the \"(default)\" wording (never \"(not set)\").
    assert "get modelPlaceholder()" in js
    assert "`${this.defaultModel} (default)`" in js
    assert "'(default)'" in js
    assert "'(not set)'" not in js


def test_index_html_wires_pending_change_ui():
    """The drawer surfaces staged changes (pending badges/notes + a Cancel
    action for the staged default) until Save persists them."""
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert "provider-pending-badge" in html
    assert "pending-note" in html
    assert "unstageDefault()" in html


def test_api_key_status_line_has_no_pending_change_badge():
    """The API-key status line no longer carries a "Key Changed (pending on
    save)" badge — the staged change is surfaced only by the pending note.
    The line itself reports the stored state neutrally: "no key stored for
    this provider" when the provider has no key set (suppressed while a key
    is staged so it cannot contradict the pending note)."""
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    # The pending-change claim badge is gone entirely...
    assert "Key Changed (pending on save)" not in html
    # The neutral "key configured" status was removed too...
    assert "key configured" not in html
    # ...and the unset state is still reported for key-less providers,
    # suppressed while a key is staged for the selected provider (so it
    # never contradicts the pending note).
    assert "!selectedProviderDetail.api_key_set" in html
    assert "pendingApiKey && pendingApiKey.provider === selectedProvider" in html
