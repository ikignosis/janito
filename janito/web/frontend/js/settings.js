// SettingsPanel Alpine component — change provider, model, endpoint, etc.

function settingsComponent() {
    return {
        open: false,
        config: {},
        status: {},
        providers: [],
        model: '',
        selectedProvider: '',
        saving: false,
        settingDefault: false,
        message: null,

        // "Set API Key" modal state
        keyModalOpen: false,
        keyInput: '',
        keyReveal: false,
        keySaving: false,
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
                this.model = this.config.model || '';
                // Default the combo to the provider actually in use (a
                // session-only override wins over the persisted default).
                this.selectedProvider =
                    (this.providers.find((p) => p.effective) || {}).name ||
                    this.config.provider ||
                    (this.providers.find((p) => p.active) || {}).name ||
                    '';
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
        // picked provider's configured model so the Model field always
        // describes the provider being edited (keeping a model name from
        // the previous provider would make the next API call fail).
        onProviderChange() {
            const p = this.providers.find((x) => x.name === this.selectedProvider);
            this.model = (p && p.model) || '';
        },

        // The provider object currently selected in the combobox (or null).
        get selectedProviderDetail() {
            return (
                this.providers.find((p) => p.name === this.selectedProvider) ||
                null
            );
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

        // Transient confirmation shown after Set Default / Set API Key
        // succeed.  (Note the trailing colon — "…failed:" errors must NOT
        // render in the green confirmation style.)
        get hintMessage() {
            const confirmPrefixes = ['Set default:', 'API key updated:'];
            return this.message &&
                confirmPrefixes.some((p) => this.message.startsWith(p))
                ? this.message
                : null;
        },

        // Auto-expiring inline feedback (same behaviour as save()).
        _announce(text) {
            this.message = text;
            setTimeout(() => {
                if (this.message === text) this.message = null;
            }, 2500);
        },

        // Promote the selected provider to the default: persisted to
        // ~/.janito/config.json and applied to this running server, so the
        // next prompt already uses it — no restart needed.
        async setDefaultProvider() {
            if (this.settingDefault) return;
            this.settingDefault = true;
            try {
                const data = await Api.setDefaultProvider(this.selectedProvider);
                const p = this.providers.find((x) => x.name === data.provider);
                this.providers.forEach((x) => { x.active = x === p; });
                if (p) p.model = data.model || p.model;
                // Reflect the new default into the status bar and the
                // chat-page provider combo.
                if (this.$dispatch) {
                    this.$dispatch('config-updated', { provider: data.provider });
                    this.$dispatch('janito-provider-changed', {
                        provider: data.provider,
                        model: data.model,
                    });
                }
                this._announce(`Set default: ${data.provider}`);
            } catch (e) {
                // The server may have rejected the switch (e.g. the provider
                // has no API key): re-read the providers so the combo and the
                // drawer agree on the true default again.
                window.dispatchEvent(new CustomEvent('config-updated'));
                this.message = 'Set default failed: ' + e.message;
            } finally {
                this.settingDefault = false;
            }
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
            if (this.keySaving) return;
            this.keyModalOpen = false;
            this.keyError = null;
            this.keyInput = '';
        },

        // Persist the typed key for the selected provider.  The backend
        // writes it to ~/.janito/auth.json; the OpenAI client resolves the
        // key per call, so it applies to the very next prompt — no restart.
        async saveApiKey() {
            if (this.keySaving) return;
            const key = this.keyInput.trim();
            if (!key) {
                this.keyError = 'Please paste an API key first.';
                return;
            }
            this.keySaving = true;
            this.keyError = null;
            try {
                const data = await Api.setApiKey(this.selectedProvider, key);
                // Refresh the masked value + per-provider "key set" flags.
                await this.load();
                this.keyModalOpen = false;
                this.keyInput = '';
                this._announce(`API key updated: ${data.provider}`);
            } catch (e) {
                this.keyError = 'Failed to save the key: ' + e.message;
            } finally {
                this.keySaving = false;
            }
        },

        async save() {
            this.saving = true;
            this.message = null;
            try {
                const updated = await Api.patchConfig({
                    model: this.model,
                });
                this.message = 'Saved: ' + Object.keys(updated.updated).join(', ');
                // Reflect into the status bar / root config
                if (this.$dispatch) {
                    this.$dispatch('config-updated', updated.updated);
                }
                setTimeout(() => { this.message = null; }, 2500);
            } catch (e) {
                this.message = 'Save failed: ' + e.message;
            } finally {
                this.saving = false;
            }
        },

        close() { this.open = false; },
    };
}
