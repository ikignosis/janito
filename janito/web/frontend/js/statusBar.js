// StatusBar Alpine component — model, provider, tokens, CLI flags, connection.

function statusBarComponent() {
    return {
        config: {},
        status: {},
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

        // Effective model name, or null when nothing is configured yet
        // (CLI --model, runtime config, or server status).  The template
        // renders a muted "(not set)" placeholder in that case.
        get model() {
            return this.config.model || this.status.model || null;
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
