// SettingsPanel Alpine component — change provider, model, endpoint, etc.

function settingsComponent() {
    return {
        open: false,
        config: {},
        status: {},
        providers: [],
        model: '',
        thinking: false,
        verbose: false,
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
                this.providers = (await Api.getProviders()).providers || [];
                this.model = this.config.model || '';
                this.thinking = !!this.config.thinking;
                this.verbose = !!this.config.verbose;
            } catch (e) {
                this.message = 'Failed to load settings: ' + e.message;
            }
        },

        async save() {
            this.saving = true;
            this.message = null;
            try {
                const updated = await Api.patchConfig({
                    model: this.model,
                    thinking: this.thinking,
                    verbose: this.verbose,
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
