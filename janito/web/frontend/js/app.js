// Root Alpine.js component — layout + drawers only.
//
// Session/chat orchestration is intentionally NOT done here via x-ref.
// In Alpine 3 an x-ref placed on the same element as a nested x-data is
// registered on that nested component, not the parent — so the parent cannot
// reach child component data through $refs. Instead, components communicate
// through window CustomEvents (see sessions.js and chat.js):
//
//   sessions.js  -> 'janito-open-session'   (chat.js listens, connects WS)
//   chat.js      -> 'janito-sessions-refresh' (sessions.js listens, reloads)
//   chat.js      -> 'janito-connection', 'janito-usage' (statusBar listens)
//
// $root is used by children for drawer/sidebar toggles (reliable Alpine magic).

function appComponent() {
    return {
        sidebarOpen: true,
        settingsOpen: false,
        mcpOpen: false,

        toggleSettings() {
            this.settingsOpen = !this.settingsOpen;
            if (this.mcpOpen) this.mcpOpen = false;
        },

        toggleMcp() {
            this.mcpOpen = !this.mcpOpen;
            if (this.settingsOpen) this.settingsOpen = false;
        },

        closeDrawers() {
            this.settingsOpen = false;
            this.mcpOpen = false;
        },

        toggleSidebar() {
            this.sidebarOpen = !this.sidebarOpen;
        },
    };
}
