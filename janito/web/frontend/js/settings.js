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

        async load() {
            try {
                this.config = await Api.getConfig();
                this.status = await Api.getStatus();
                const data = await Api.getProviders();
                this.providers = data.providers || [];
                this.model = this.config.model || '';
                this.selectedProvider =
                    this.config.provider || this.status.active_provider || '';
            } catch (e) {
                this.message = 'Failed to load settings: ' + e.message;
            }
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
                // Reflect the new default into the status bar.
                if (this.$dispatch) {
                    this.$dispatch('config-updated', { provider: data.provider });
                }
                this._announce(`Set default: ${data.provider}`);
            } catch (e) {
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
                this.status = await Api.getStatus();
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
