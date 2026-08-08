// StatusBar Alpine component — model, provider, tokens, CLI flags, connection.

function statusBarComponent() {
    return {
        config: {},
        status: {},
        providers: [],          // provider list from GET /api/config/providers
        connection: 'disconnected',
        lastUsage: null,

        init() {
            this.load();
            // Refresh when config changes from the settings panel
            window.addEventListener('config-updated', () => this.load());
            // Refresh when the provider is switched from the chat-page combo
            window.addEventListener('janito-provider-changed', () => this.load());
            // Connection state broadcast from the chat component
            window.addEventListener('janito-connection', (e) => {
                this.connection = e.detail;
            });
            // Last usage broadcast from the chat component
            window.addEventListener('janito-usage', (e) => {
                this.lastUsage = e.detail;
            });
        },

        async load() {
            try {
                this.config = await Api.getConfig();
                this.status = await Api.getStatus();
                // Needed to resolve the selected provider's default model.
                this.providers = (await Api.getProviders()).providers || [];
            } catch (e) {
                console.error('Failed to load status:', e);
            }
        },

        get provider() {
            // ``status.provider`` is the *effective* provider — the one the
            // next prompt uses (a session-only combo override wins over the
            // persisted default, which lives in ``active_provider``).
            return (
                this.status.provider ||
                this.status.active_provider ||
                this.config.provider ||
                '?'
            );
        },

        // The provider object the status bar currently describes (the
        // effective provider), or null before the providers list loads.
        get providerDetail() {
            return this.providers.find((p) => p.name === this.provider) || null;
        },

        // The effective API type for the selected provider: the configured
        // override first (``api_type``), then the provider's built-in
        // default (the first of its ``supported_api_types``) — mirrors the
        // backend's ``resolve_api_type`` resolution and the Settings
        // drawer's combobox, so the badge shows the API the next prompt
        // actually uses.
        get apiType() {
            const p = this.providerDetail;
            if (!p) return '';
            return (
                p.api_type ||
                p.default_api_type ||
                (p.supported_api_types && p.supported_api_types[0]) ||
                ''
            );
        },

        // The model the selected provider falls back to when nothing is
        // configured: its configured override first, then its built-in
        // default (mirrors the provider switcher / settings resolution).
        get defaultModel() {
            const p = this.providerDetail;
            return (p && (p.model || p.default_model)) || null;
        },

        // Effective model name, or null when nothing is configured at all
        // (CLI --model, runtime config, server status, or the selected
        // provider's default).  When only the provider's default applies,
        // the template renders it muted with a "(default)" marker instead
        // of "(not set)".
        get model() {
            return (
                this.config.model ||
                this.status.model ||
                this.defaultModel ||
                null
            );
        },

        // True while the shown model is the provider's fallback default and
        // NOT an explicitly configured/CLI model (drives the "(default)"
        // marker in the template).
        get modelIsDefault() {
            return !(this.config.model || this.status.model) && !!this.defaultModel;
        },

        get privileges() {
            return this.config.privileges || this.status.privileges || {};
        },

        // Toggle thinking mode at runtime (status-bar badge).  The change is
        // in-memory on the server (POST /api/config/thinking) and applies to
        // the very next prompt; it is NOT persisted to ~/.janito/config.json
        // and is lost on restart — like the session-only provider switch.
        // ``effective`` is what the next prompt actually uses, so the badge
        // mirrors that value.
        async toggleThinking() {
            const next = !this.config.thinking;
            try {
                const data = await Api.setThinking(next);
                this.config.thinking = data.effective;
            } catch (e) {
                console.error('Failed to toggle thinking:', e);
            }
        },
    };
}
