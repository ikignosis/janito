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

        // Transient "X is the default" confirmation shown after Set Default.
        // (Note the trailing colon — "Set default failed:" errors must NOT
        // render in the green confirmation style.)
        get hintMessage() {
            return this.message && this.message.startsWith('Set default:')
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
