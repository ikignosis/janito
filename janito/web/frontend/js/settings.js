// SettingsPanel Alpine component — change provider, model, endpoint, etc.

function settingsComponent() {
    return {
        open: false,
        config: {},
        status: {},
        providers: [],
        model: '',
        // Pristine baseline the drawer loaded with: the Save button stays
        // disabled until the drawer holds unsaved changes (issue #38).
        originalModel: '',
        // Staged (unsaved) changes. "Set Default" and "Set API Key" no
        // longer write to disk the moment they are clicked — they arm the
        // Save button, and the changes are persisted only when it is
        // clicked (POST /api/config/default-provider, /api/config/api-key).
        defaultChanged: false,
        pendingDefaultProvider: null,   // provider staged to become the default
        pendingApiKey: null,            // { provider, key } staged API key
        selectedProvider: '',
        saving: false,
        message: null,

        // "Set API Key" modal state
        keyModalOpen: false,
        keyInput: '',
        keyReveal: false,
        keyError: null,

        async toggle() {
            this.open = !this.open;
            if (this.open) await this.load();
        },

        init() {
            // The API-key field describes the provider picked in the
            // combobox, so reload it whenever the selection changes.
            this.$watch('selectedProvider', () => this.refreshStatus());
        },

        async load() {
            try {
                this.config = await Api.getConfig();
                const data = await Api.getProviders();
                this.providers = data.providers || [];
                // Keep the combo where the user left it (e.g. a non-default
                // provider they are configuring) across a save's re-baseline;
                // only default to the provider actually in use (a session-only
                // override wins over the persisted default) when nothing is
                // selected yet or the current pick left the list.
                const current = this.selectedProvider;
                this.selectedProvider =
                    this.providers.some((p) => p.name === current)
                        ? current
                        : (this.providers.find((p) => p.effective) || {}).name ||
                          this.config.provider ||
                          (this.providers.find((p) => p.active) || {}).name ||
                          '';
                // The Model field always carries the model the next prompt
                // would actually use as its VALUE: an explicit override
                // first, otherwise the selected provider's configured /
                // built-in default (no longer hidden in a placeholder).
                this.model = this.config.model || this.defaultModel || '';
                // Record the pristine baseline: nothing to save yet, so the
                // Save button starts (and stays) disabled until the model
                // changes, a default is staged, or an API key is staged.
                this.originalModel = this.model;
                this.defaultChanged = false;
                this.pendingDefaultProvider = null;
                this.pendingApiKey = null;
                this.status = await Api.getStatus(this.selectedProvider);
            } catch (e) {
                this.message = 'Failed to load settings: ' + e.message;
            }
        },

        // Refresh the API-key status for the currently selected provider
        // (falls back to the active/default provider when nothing is picked).
        async refreshStatus() {
            try {
                this.status = await Api.getStatus(this.selectedProvider);
            } catch (e) {
                // Keep the stale status visible on failure.
            }
        },

        // Called from the provider <select>'s @change: adopt the newly
        // picked provider's configured model (or its built-in default) so
        // the Model field always shows a value and describes the provider
        // being edited (keeping a model name from the previous provider
        // would make the next API call fail).
        onProviderChange() {
            const p = this.providers.find((x) => x.name === this.selectedProvider);
            this.model = (p && (p.model || p.default_model)) || '';
        },

        // The provider object currently selected in the combobox (or null).
        get selectedProviderDetail() {
            return (
                this.providers.find((p) => p.name === this.selectedProvider) ||
                null
            );
        },

        // The model the selected provider falls back to when the override
        // field is empty: the provider's configured model first, then its
        // built-in default (mirrors the provider switcher's resolution).
        get defaultModel() {
            const p = this.selectedProviderDetail;
            return (p && (p.model || p.default_model)) || null;
        },

        // Fallback hint for the Model field, shown only while the field is
        // empty (e.g. the user cleared it, or the provider has no default):
        // names the model the next prompt would fall back to, with a
        // "(default)" marker, instead of "(not set)".
        get modelPlaceholder() {
            return this.defaultModel ? `${this.defaultModel} (default)` : '(not set)';
        },

        // The provider currently flagged as the default (or null if the list
        // hasn't loaded yet / the default isn't in the known list).
        get defaultProviderDetail() {
            return this.providers.find((p) => p.active) || null;
        },

        // True while a non-default provider is picked and the combo sits
        // in the "not the default provider" state.
        get showSetDefault() {
            return (
                !!this.selectedProviderDetail &&
                !this.selectedProviderDetail.active
            );
        },

        // True while the combo shows the provider staged to become the
        // default (drives the "default pending" badge + Cancel button).
        get isStagedProviderSelected() {
            return (
                !!this.pendingDefaultProvider &&
                this.pendingDefaultProvider === this.selectedProvider
            );
        },

        // True while the selected provider has an API key stored, so it can
        // actually be promoted to the default (mirrors the backend guard:
        // saving without a key would be rejected with 400).
        get selectedProviderHasKey() {
            return !!(
                this.selectedProviderDetail && this.selectedProviderDetail.api_key_set
            );
        },

        // True while an API key is staged but not yet written to auth.json.
        get apiKeyChanged() {
            return !!this.pendingApiKey;
        },

        // True while the drawer holds unsaved changes: the model field
        // differs from the value it loaded with, a different provider was
        // staged as the default, or an API key was staged.  The Save button
        // is disabled until one of these happens (issue #38).
        get canSave() {
            return (
                this.model !== this.originalModel ||
                this.defaultChanged ||
                this.apiKeyChanged
            );
        },

        // Transient confirmation shown after a successful save.  (Note the
        // trailing colon — "…failed:" errors must NOT render in the green
        // confirmation style.)
        get hintMessage() {
            const confirmPrefixes = ['Saved:'];
            return this.message &&
                confirmPrefixes.some((p) => this.message.startsWith(p))
                ? this.message
                : null;
        },

        // Stage the selected provider as the new default.  Nothing is
        // written to ~/.janito/config.json here — the Save button persists
        // it (POST /api/config/default-provider) and re-baselines the
        // drawer, so the next prompt uses it — no restart needed.
        setDefaultProvider() {
            const p = this.selectedProviderDetail;
            if (!p) return;
            if (!p.api_key_set) {
                this.message = 'Set default failed: no API key is set for this provider.';
                return;
            }
            // A different provider is now staged as the default: the drawer
            // holds unsaved changes, so arm the Save button.  Also adopt the
            // provider's configured model (or its built-in default) into the
            // field so it stays in sync with what the next prompt would use
            // once saved.
            this.pendingDefaultProvider = p.name;
            this.defaultChanged = true;
            this.model = (p.model || p.default_model) || this.model;
        },

        // Discard a staged default-provider change (the drawer stays open;
        // nothing was written to disk yet).
        unstageDefault() {
            this.pendingDefaultProvider = null;
            this.defaultChanged = false;
        },

        // ---- "Set API Key" modal ----------------------------------------

        // Open the modal pre-targeted at the provider selected in the combo
        // (falling back to the default provider while nothing is picked).
        openKeyModal() {
            if (!this.selectedProvider) return;
            this.keyInput = '';
            this.keyReveal = false;
            this.keyError = null;
            this.keyModalOpen = true;
            this.$nextTick(() => {
                if (this.$refs.keyInput) this.$refs.keyInput.focus();
            });
        },

        closeKeyModal() {
            this.keyModalOpen = false;
            this.keyError = null;
            this.keyInput = '';
        },

        // Stage the typed key for the selected provider.  Nothing is written
        // to ~/.janito/auth.json here — the Save button persists it
        // (POST /api/config/api-key) and re-baselines the drawer.
        saveApiKey() {
            const key = this.keyInput.trim();
            if (!key) {
                this.keyError = 'Please paste an API key first.';
                return;
            }
            this.pendingApiKey = { provider: this.selectedProvider, key };
            this.keyModalOpen = false;
            this.keyInput = '';
        },

        // Persist every staged/edited change with one Save click: the model
        // override, the staged default provider, and the staged API key.
        async save() {
            this.saving = true;
            this.message = null;
            try {
                const saved = [];

                // 1. Promote the staged provider to the persisted default
                //    first, so the model override below lands on the
                //    provider being defaulted.
                if (this.defaultChanged && this.pendingDefaultProvider) {
                    const data = await Api.setDefaultProvider(this.pendingDefaultProvider);
                    saved.push(`default: ${data.provider}`);
                }

                // 2. Persist the model override (if the field changed).
                if (this.model !== this.originalModel) {
                    const updated = await Api.patchConfig({ model: this.model });
                    saved.push(...Object.keys(updated.updated));
                }

                // 3. Store the staged API key (per-provider; independent of
                //    the default-provider change above).
                if (this.pendingApiKey) {
                    await Api.setApiKey(this.pendingApiKey.provider, this.pendingApiKey.key);
                    saved.push(`api key: ${this.pendingApiKey.provider}`);
                }

                // Reflect into the status bar / root config.
                if (this.$dispatch) {
                    this.$dispatch('config-updated', {
                        provider: this.pendingDefaultProvider,
                    });
                    this.$dispatch('janito-provider-changed', {
                        provider: this.pendingDefaultProvider,
                        model: this.model,
                    });
                }

                // Re-read the server state (new default, key status) so the
                // drawer, combo and status bar all agree again.
                try {
                    await this.load();
                } catch (e) {
                    // Non-fatal: keep the saved confirmation.
                }

                // The drawer is pristine again: disable the Save button until
                // the next edit, default stage, or key stage.
                this.originalModel = this.model;
                this.defaultChanged = false;
                this.pendingDefaultProvider = null;
                this.pendingApiKey = null;
                this.message = 'Saved: ' + saved.join(', ');
                setTimeout(() => { this.message = null; }, 2500);
            } catch (e) {
                // The server may have rejected (or partially applied) the
                // changes: re-read the providers so the drawer and the
                // server agree on the true state again.
                window.dispatchEvent(new CustomEvent('config-updated'));
                this.message = 'Save failed: ' + e.message;
            } finally {
                this.saving = false;
            }
        },

        close() { this.open = false; },
    };
}
