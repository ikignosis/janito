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
// $root is NOT used for cross-component access. In Alpine 3 $root resolves to
// the INNERMOST x-data scope (not the outermost/root one), so $root.toggleTheme
// inside a nested child component would fail. Instead, expressions reference
// this component's methods/props bare (e.g. @click="toggleTheme()"); Alpine's
// scope merging walks up the DOM to find them on the parent x-data.
//
// Theme
// -----
// Two palettes live in css/theme.css: `:root` (light, the default) and
// `html[data-theme="dark"]` (dark, the original janito CLI look). The choice
// is persisted in localStorage and, to avoid a flash of the wrong theme,
// restored BEFORE first paint by a tiny inline script in index.html. Here we
// simply mirror that state so the topbar switcher can bind to it.

function appComponent() {
    return {
        sidebarOpen: true,
        settingsOpen: false,
        mcpOpen: false,
        theme: 'light',          // 'light' | 'dark' — synced to <html data-theme>
        toast: null,             // { kind: 'ok'|'error', text } while shown
        _toastTimer: null,

        init() {
            // Pick up whatever the pre-paint script (or the absence of it) set.
            this.theme = document.documentElement.getAttribute('data-theme') === 'dark'
                ? 'dark'
                : 'light';

            // Transient notifications broadcast by nested components
            // (e.g. the provider switcher).  The toast element lives at the
            // root of this component (bottom of index.html).
            window.addEventListener('janito-toast', (e) => this.showToast(e.detail));
        },

        showToast(detail) {
            const kind = (detail && detail.kind) || 'ok';
            const text = (detail && detail.text) || '';
            if (this._toastTimer) clearTimeout(this._toastTimer);
            this.toast = { kind, text };
            this._toastTimer = setTimeout(() => {
                this.toast = null;
                this._toastTimer = null;
            }, 3000);
        },

        setTheme(theme) {
            this.theme = theme;
            if (theme === 'dark') {
                document.documentElement.setAttribute('data-theme', 'dark');
            } else {
                document.documentElement.removeAttribute('data-theme');
            }
            try {
                localStorage.setItem('janito-theme', theme);
            } catch (e) { /* storage unavailable — theme just won't persist */ }
        },

        toggleTheme() {
            this.setTheme(this.theme === 'dark' ? 'light' : 'dark');
        },

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
