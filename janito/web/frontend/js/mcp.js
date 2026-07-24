// McpPanel Alpine component — service status/toggles.

function mcpComponent() {
    return {
        open: false,
        services: [],
        connectedCount: 0,
        loading: false,
        busy: null,
        message: null,

        async toggle() {
            this.open = !this.open;
            if (this.open) await this.load();
        },

        async load() {
            this.loading = true;
            try {
                const data = await Api.getMcpServices();
                this.services = data.services || [];
                this.connectedCount = data.connected_count || 0;
            } catch (e) {
                this.message = 'Failed to load MCP services: ' + e.message;
            } finally {
                this.loading = false;
            }
        },

        async connect(name) {
            this.busy = name;
            this.message = null;
            try {
                await Api.connectMcp(name);
                await this.load();
            } catch (e) {
                this.message = `Connect failed: ${e.message}`;
            } finally {
                this.busy = null;
            }
        },

        async disconnect(name) {
            this.busy = name;
            this.message = null;
            try {
                await Api.disconnectMcp(name);
                await this.load();
            } catch (e) {
                this.message = `Disconnect failed: ${e.message}`;
            } finally {
                this.busy = null;
            }
        },

        close() { this.open = false; },
    };
}
