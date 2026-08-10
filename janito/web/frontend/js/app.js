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
//   chat.js      -> 'janito-session-title'  (sessions.js listens, patches label)
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
        // In-browser question from the assistant (AskUser tool):
        // { sessionId, prompt_id, question, title } while the panel is open.
        promptModal: null,
        promptAnswer: '',        // the answer the user is typing

        init() {
            // Pick up whatever the pre-paint script (or the absence of it) set.
            this.theme = document.documentElement.getAttribute('data-theme') === 'dark'
                ? 'dark'
                : 'light';

            // Transient notifications broadcast by nested components
            // (e.g. the provider switcher).  The toast element lives at the
            // root of this component (bottom of index.html).
            window.addEventListener('janito-toast', (e) => this.showToast(e.detail));

            // The assistant asked the user a question (AskUser tool). Shown
            // by the chat component's event router, but the panel lives here
            // (root scope) so it appears even when the asking session is in
            // the background.
            window.addEventListener('janito-prompt', (e) => {
                this.promptModal = e.detail || null;
                this.promptAnswer = '';
                this.$nextTick(() => {
                    const el = document.getElementById('prompt-panel-input');
                    if (el) el.focus();
                });
            });

            // A turn finished / was cancelled / errored while the panel was
            // open (e.g. Ctrl+C): the backend has already resolved the
            // question as empty, so close the panel. Scoped to the raising
            // session so a background turn finishing never closes another
            // session's open question.
            window.addEventListener('janito-prompt-dismiss', (e) => {
                const sid = e.detail && e.detail.sessionId;
                if (sid && this.promptModal && this.promptModal.sessionId !== sid) {
                    return; // a different session's question is still open
                }
                this.promptModal = null;
                this.promptAnswer = '';
            });
        },

        // Render the question text as markdown (same helper the chat uses).
        renderPromptQuestion(text) {
            return window.JanitoMarkdown
                ? window.JanitoMarkdown.render(text || '')
                : (text || '');
        },

        // Send the typed answer back to the session that asked, then close.
        submitPromptAnswer() {
            if (!this.promptModal) return;
            window.dispatchEvent(new CustomEvent('janito-prompt-answer', {
                detail: { ...this.promptModal, answer: this.promptAnswer },
            }));
            this.promptModal = null;
            this.promptAnswer = '';
        },

        // Dismiss without answering: the tool receives an empty answer.
        dismissPrompt() {
            if (!this.promptModal) return;
            window.dispatchEvent(new CustomEvent('janito-prompt-answer', {
                detail: { ...this.promptModal, answer: '' },
            }));
            this.promptModal = null;
            this.promptAnswer = '';
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
