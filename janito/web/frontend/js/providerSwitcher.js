// ProviderSwitcher Alpine component — pick the provider right from the
// chat page (issue #34).
//
// The combo in the topbar lists exactly the providers that have an API key
// stored in ~/.janito/auth.json (GET /api/config/providers -> api_key_set).
// Picking a provider switches it for THIS browser/server session only via
// POST /api/config/session-provider, which is applied to the running server
// but never written to ~/.janito/config.json — so the very next prompt uses
// it, yet it does not leak into future CLI/web runs and is lost on restart.
// (Persisting a default is the Settings drawer's explicit "Set Default".)
//
// The combo's selected value follows the provider flagged `effective` —
// the one the next prompt actually resolves to (the session override, or the
// persisted default when there is none).
//
// Events dispatched on success/failure:
//   janito-provider-changed  { provider, model }   — status bar reloads
//   janito-toast             { kind, text }        — app root renders a toast
//
// A 'config-updated' event (Settings drawer saved / set a key / changed the
// default) triggers a silent re-read so the combo never shows a stale list.

function providerSwitcherComponent() {
    return {
        providers: [],          // full list from GET /api/config/providers
        selected: '',           // effective provider name (in use right now)
        busy: false,            // a switch request is in flight
        locked: false,           // active conversation already has messages
        sessionId: null,

        init() {
            this.load();
            window.addEventListener('config-updated', () => this.load());
            window.addEventListener('janito-session-lock', (e) => {
                const d = e.detail || {};
                this.sessionId = d.sessionId || null;
                this.locked = !!d.locked;
                if (d.provider) this.selected = d.provider;
            });
        },

        // Providers worth offering in the combo: the ones with an API key
        // set, plus the current effective selection (kept even if its key
        // was removed, so the combo always has a valid selected value).
        get available() {
            return this.providers.filter(
                (p) => p.api_key_set || p.name === this.selected
            );
        },

        get selectedDetail() {
            return this.providers.find((p) => p.name === this.selected) || null;
        },

        // Effective model for the selected provider: the per-provider
        // configured model, falling back to the provider's built-in default.
        get selectedModel() {
            const p = this.selectedDetail;
            return (p && (p.model || p.default_model)) || null;
        },

        async load() {
            try {
                const data = await Api.getProviders();
                this.providers = data.providers || [];
                // Select the provider the next prompt resolves to (session
                // override wins over the persisted default).
                const effective =
                    this.providers.find((p) => p.effective) ||
                    this.providers.find((p) => p.active);
                if (effective) this.selected = effective.name;
            } catch (e) {
                console.error('Failed to load providers:', e);
            }
        },

        _toast(kind, text) {
            window.dispatchEvent(
                new CustomEvent('janito-toast', { detail: { kind, text } })
            );
        },

        async applyProvider() {
            const name = this.selected;
            if (!name || this.busy || this.locked) return;

            // Re-selecting the provider already in use is a no-op.
            const detail = this.providers.find((p) => p.name === name);
            if (detail && detail.effective) return;

            this.busy = true;
            const previous =
                (this.providers.find((p) => p.effective) ||
                    this.providers.find((p) => p.active) || {}).name || '';
            try {
                const data = await Api.setSessionProvider(name, this.sessionId);
                // Reflect the new effective provider locally, adopt its model.
                this.providers.forEach((p) => {
                    p.effective = p.name === data.provider;
                });
                const p = this.providers.find((x) => x.name === data.provider);
                if (p && data.model !== undefined) p.model = data.model;

                window.dispatchEvent(
                    new CustomEvent('janito-provider-changed', {
                        detail: { provider: data.provider, model: data.model },
                    })
                );
                this._toast(
                    'ok',
                    `Provider switched to ${data.provider} (this session)` +
                        (data.model ? ` · ${data.model}` : '')
                );
            } catch (e) {
                // Revert the combo to the effective provider.
                this.selected = previous;
                this._toast('error', `Switch failed: ${e.message}`);
            } finally {
                this.busy = false;
            }
        },
    };
}
