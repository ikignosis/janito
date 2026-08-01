"""Frontend wiring tests for the Settings drawer Save button (issue #38).

The Settings drawer's Save button must start disabled and only become
enabled when the drawer actually holds unsaved changes: the model field
differs from the value it loaded with, a different provider was staged as
the default via "Set Default", or an API key was staged via "Set API Key".

"Set Default" and "Set API Key" never write to disk the moment they are
clicked — they only arm the Save button (the changes are staged in the
component).  A successful save applies every staged change (default
provider, model, API key) and re-baselines the drawer, disabling Save
again.  The re-baseline keeps the provider combo where the user left it —
it only snaps back to the default/effective provider when nothing is
selected yet or the pick left the providers list.

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
    assert "this.model = (p.model || p.default_model) || this.model;" in js
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
    # The model is persisted scoped to the provider the field describes
    # (the combo's selection) so it lands under the right provider key.
    assert "await Api.patchConfig({" in js
    assert "model: this.model" in js
    assert "provider: this.selectedProvider" in js
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


def test_load_keeps_selected_provider_across_rebaseline():
    """Re-loading the drawer (e.g. the re-baseline after a save) keeps the
    provider combo where the user left it instead of snapping back to the
    default/effective provider; the effective provider is only the fallback
    when nothing is selected yet or the current pick left the list.
    """
    js = _settings_js()
    # The current selection is captured before the combo is re-assigned...
    assert "const current = this.selectedProvider;" in js
    # ...and kept when it is still in the freshly loaded providers list...
    assert "this.providers.some((p) => p.name === current)" in js
    # ...with the effective provider as the fallback only.
    assert "this.providers.find((p) => p.effective)" in js


def test_index_html_disables_save_until_dirty():
    """The Save button is bound to the canSave computed property."""
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert ':disabled="saving || !canSave"' in html


def test_model_field_shows_default_model_as_value():
    """The Model field carries the default model as its VALUE (pre-filled
    when no override is set) instead of hiding it in a placeholder."""
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert 'x-model="model"' in html
    # The default model lives in the field value now; the placeholder is
    # only a fallback hint for an emptied field.
    assert ":placeholder=" in html
    assert 'placeholder="(not set)"' not in html


def test_settings_js_prefills_model_with_default():
    """The drawer resolves the effective model (configured override first,
    then the provider's built-in default — the same resolution the topbar
    provider switcher uses) and puts it in the field VALUE so the drawer
    always shows which model the next prompt would actually use."""
    js = _settings_js()
    # Resolution mirrors the provider switcher: configured model first,
    # falling back to the provider's built-in default.
    assert "get defaultModel()" in js
    assert "p.model || p.default_model" in js
    # The field value is pre-filled from the selected provider's own model
    # (configured override or built-in default); the running server's model
    # is only a last-resort fallback (it may belong to a different provider).
    assert "this.model = this.defaultModel || this.config.model || '';" in js
    # ...adopting another provider keeps showing a value (configured or
    # built-in default), never an empty field...
    assert "this.model = (p && (p.model || p.default_model)) || '';" in js
    # ...and staging a default adopts the same resolved model.
    assert "this.model = (p.model || p.default_model) || this.model;" in js
    # The placeholder remains only as a fallback hint for an emptied field
    # (it names the default with a "(default)" marker).
    assert "get modelPlaceholder()" in js
    assert "`${this.defaultModel} (default)`" in js


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
