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
