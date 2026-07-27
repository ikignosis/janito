// SessionSidebar Alpine component — list/create/delete conversations.
//
// Communicates with chat.js via window CustomEvents:
//   'janito-open-session'    -> chat.js connects WebSocket
//   'janito-sessions-refresh' -> this component reloads (sent by chat.js)

function sessionsComponent() {
    return {
        sessions: [],
        activeId: null,
        loading: false,
        _bootstrapped: false,
        _indicators: {},

        init() {
            // Reload when chat.js signals a change (e.g. auto-title, new session)
            window.addEventListener('janito-sessions-refresh', () => this.load());

            // A session vanished on the server (e.g. server restarted) —
            // re-bootstrap: reload the live session list and pick/create one.
            window.addEventListener('janito-session-lost', (e) => this._recover(e.detail));

            // Per-session status updates from chat.js (for sidebar indicators:
            // spinner while a background tab is processing, dot when finished).
            window.addEventListener('janito-session-status', (e) => this._onStatusChange(e.detail.id, e.detail.status));

            // Self-bootstrap: load sessions and open the most recent (or create new)
            this.$nextTick(() => this.bootstrap());
        },

        async _recover(lostId) {
            console.warn('[sessions] recovering from lost session', lostId);
            if (this.activeId === lostId) this.activeId = null;
            await this.load();
            if (this.sessions.length > 0) {
                this.select(this.sessions[0].session_id);
            } else {
                await this.create();
            }
        },

        async bootstrap() {
            if (this._bootstrapped) return;
            this._bootstrapped = true;

            await this.load();
            if (this.sessions.length > 0) {
                this.select(this.sessions[0].session_id);
            } else {
                await this.create();
            }
        },

        async load() {
            this.loading = true;
            try {
                const data = await Api.listSessions();
                this.sessions = (data.sessions || []).sort(
                    (a, b) => b.last_active - a.last_active
                );
            } catch (e) {
                console.error('Failed to load sessions:', e);
            } finally {
                this.loading = false;
            }
        },

        async create() {
            try {
                const session = await Api.createSession();
                await this.load();
                this.select(session.session_id);
            } catch (e) {
                console.error('Failed to create session:', e);
            }
        },

        select(id) {
            this.activeId = id;
            delete this._indicators[id];
            // Tell chat.js to connect to this session
            window.dispatchEvent(new CustomEvent('janito-open-session', { detail: id }));
        },

        _onStatusChange(id, status) {
            // Active tab needs no indicator - the user is already viewing it.
            if (id === this.activeId) return;

            const processing = ['waiting', 'streaming', 'tool_running'];
            if (processing.includes(status)) {
                this._indicators[id] = 'spinner';
            } else if (status === 'idle') {
                // Only show a dot if the session was previously processing.
                if (this._indicators[id] === 'spinner') {
                    this._indicators[id] = 'dot';
                }
            }
        },

        indicatorState(id) {
            return this._indicators[id] || null;
        },

        async remove(id, event) {
            event.stopPropagation();
            try {
                await Api.deleteSession(id);
                delete this._indicators[id];
                await this.load();
                // Tell chat.js to release this session's socket/store, whether
                // or not it is the currently active tab.
                window.dispatchEvent(new CustomEvent('janito-session-deleted', { detail: id }));
                if (this.activeId === id) {
                    this.activeId = null;
                    window.dispatchEvent(new CustomEvent('janito-clear-session'));
                }
            } catch (e) {
                console.error('Failed to delete session:', e);
            }
        },

        async rename(id, event) {
            event.stopPropagation();
            const session = this.sessions.find(s => s.session_id === id);
            if (!session) return;
            const title = prompt('Rename conversation:', session.title);
            if (title !== null && title.trim()) {
                try {
                    await Api.renameSession(id, title.trim());
                    await this.load();
                } catch (e) {
                    console.error('Failed to rename session:', e);
                }
            }
        },

        timeAgo(ts) {
            const seconds = Math.floor((Date.now() / 1000) - ts);
            if (seconds < 60) return 'just now';
            if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
            if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
            return Math.floor(seconds / 86400) + 'd ago';
        },
    };
}
