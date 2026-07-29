// Chat Alpine.js component — messages, streaming, input, tool monitor.
//
// Multi-session design
// --------------------
// The app supports many open conversations, and a conversation may keep
// receiving data (tokens, tool calls, tool results) even while the user is
// looking at a *different* tab. To support that, this component keeps a
// **persistent store per session**, each with its own live WebSocket:
//
//     _sessions[sessionId] = {
//         id, messages[], status, error, connection,
//         current,      // the in-flight assistant message (or null)
//         loaded, loading, dirty
//     }
//
//   * Sockets are created once per session and are NEVER closed just because
//     the user switched tabs — so a background conversation keeps streaming
//     and its history keeps growing.
//   * Every socket event is routed to *its own* session's store via
//     `_handleEvent(event, store)`, never to shared component state.
//   * The top-level reactive properties (`messages`, `status`, `connection`,
//     `error`, `_current`) are merely a **projection of the active session**.
//     Switching tabs re-points this projection at the chosen session's store.
//
// Because `this.messages` references the active store's array, a background
// session writing to its own store never disturbs the visible tab — and when
// the user returns, the tab already contains the fully up-to-date conversation.
//
// UI state machine (per session):
//   idle -> [send prompt] -> waiting -> [first token] -> streaming
//        -> [tool_call] -> tool_running -> [tool_result] -> waiting -> streaming
//        -> [done] -> idle
//
// Module layout
// -------------
// This file is the orchestration shell. Focused concerns are split into
// sibling mixins (loaded first in index.html) and folded in via Object.assign:
//   chatFormat.js   -> window.ChatFormatMixin    (pure formatting/rendering)
//   chatMessages.js -> window.ChatMessagesMixin  (UI message/part builders)
//   chatStore.js    -> window.ChatStoreMixin     (store lifecycle, rollback)
//   chatEvents.js   -> window.ChatEventsMixin    (event dispatch table)
//   chatHistory.js  -> window.ChatHistoryMixin   (history reconstruction)
//   chatScroll.js   -> window.ChatScrollMixin    (scroll + keyboard)

// Persistent sockets live OUTSIDE the Alpine component so they are never made
// reactive (proxying a live WebSocket is undesirable). Keyed by session id.
// Exposed on window so the store mixin (_releaseSession) can reach them.
window.__janitoSessionSockets = new Map();

function chatComponent() {
    return Object.assign({
        // ---- Projection of the ACTIVE session (drives the template) ----
        messages: [],            // UI message objects for the active session
        input: '',
        status: 'idle',          // idle | waiting | streaming | tool_running
        connection: 'disconnected',  // disconnected | connecting | connected
        error: null,
        sessionId: null,         // active session id
        _current: null,          // active session's in-flight assistant message
        toolsSummary: null,      // active session's { active, skipped, skippedList }
        _followBottom: true,     // auto-follow the scroll bottom? false = user "locked" the scroll
        _scrollThreshold: 80,    // px tolerance for "at the bottom" (avoids scrollbar jitter)

        // ---- Per-session persistent state (reactive) ----
        _sessions: {},           // id -> store (see header comment)

        init() {
            // Track scroll position so we only auto-follow new content while
            // the user is "at the bottom". Scrolling up locks the view so the
            // user can read without being yanked down mid-stream.
            this.$nextTick(() => {
                const el = this.$refs.chatArea;
                if (el) el.addEventListener('scroll', () => this._updateFollowBottom());
            });

            // Session selected / created in the sidebar.
            window.addEventListener('janito-open-session', (e) => {
                this.openSession(e.detail);
            });
            // A session was deleted (release its socket/store unconditionally).
            window.addEventListener('janito-session-deleted', (e) => {
                this._releaseSession(e.detail);
            });
            // The active session was deleted -> also clear the visible view.
            window.addEventListener('janito-clear-session', () => {
                this.clearActive();
            });
        },

        // ---------------------------------------------------------------
        // Store access
        // ---------------------------------------------------------------

        // Get (or lazily create) the persistent store for a session.
        _store(id) {
            if (!this._sessions[id]) {
                this._sessions[id] = {
                    id,
                    messages: [],
                    status: 'idle',
                    error: null,
                    connection: 'disconnected',
                    current: null,
                    toolsSummary: null, // { active, skipped, skippedList } from session_start
                    loaded: false,     // history fetched from the server yet?
                    loading: false,    // a history fetch is in flight
                    dirty: false,      // user already sent a message locally
                };
            }
            return this._sessions[id];
        },

        _socket(id) {
            return window.__janitoSessionSockets.get(id) || null;
        },

        // ---------------------------------------------------------------
        // Tab switching
        // ---------------------------------------------------------------

        async openSession(id) {
            this.sessionId = id;
            const store = this._store(id);

            // Project this session's store into the visible state.
            this.messages = store.messages;
            this.status = store.status;
            this.error = store.error;
            this.connection = store.connection;
            this._current = store.current;
            this.toolsSummary = store.toolsSummary;
            this._broadcastConn();
            this._forceScrollToBottom();

            // Broadcast all session statuses so background sessions get their
            // indicators updated in the sidebar (e.g. a session that was already
            // streaming when the user switched away from it).
            this._broadcastAllStatuses();

            // Ensure this session has a live socket (created once, reused).
            if (!this._socket(id)) {
                this._createSocket(id);
            }

            // Load history exactly once per session.
            if (!store.loaded && !store.loading) {
                await this._loadHistory(id);
            }
        },

        // Create a persistent socket for a session. Its callbacks always write
        // to that session's own store, regardless of which tab is visible.
        _createSocket(id) {
            const store = this._store(id);
            const socket = new ChatSocket(id, {
                onOpen: () => {
                    store.connection = 'connected';
                    this._reflectConnection(id);
                },
                onClose: () => {
                    store.connection =
                        socket.reconnectAttempts < socket.maxReconnectAttempts
                            ? 'connecting' : 'disconnected';
                    this._reflectConnection(id);
                },
                onEvent: (event) => this._handleEvent(event, store),
            });
            window.__janitoSessionSockets.set(id, socket);
            socket.connect();
        },

        // Load a session's stored history into its store (once).
        async _loadHistory(id) {
            const store = this._store(id);
            store.loading = true;
            try {
                const session = await Api.getSession(id);
                // If the user already started chatting in this session while
                // the fetch was in flight, don't clobber their live messages.
                if (!store.dirty) {
                    const loaded = this._historyToUi(session.messages || []);
                    // Mutate in place so any `this.messages` already pointing
                    // at this array picks up the loaded content.
                    store.messages.splice(0, store.messages.length, ...loaded);
                }
                store.loaded = true;
                if (this.sessionId === id) this._forceScrollToBottom();
            } catch (e) {
                console.error('Failed to load session history:', e);
            } finally {
                store.loading = false;
            }
        },

        // ---------------------------------------------------------------
        // Sending
        // ---------------------------------------------------------------

        sendPrompt() {
            const content = this.input.trim();
            if (!content) return;
            if (this.status === 'waiting' || this.status === 'streaming') return;

            const id = this.sessionId;
            if (!id) return;
            const store = this._store(id);

            // Intercept slash commands handled entirely on the client.
            if (content.startsWith('/') && this._handleSlashCommand(content, store)) {
                this.input = '';
                this._autoResize();
                return;
            }

            store.error = null;
            this.error = null;
            store.dirty = true;   // protect the pending _loadHistory from clobbering

            // User message
            store.messages.push(this._newMessage('user', content));
            this.input = '';
            this._autoResize();
            this._forceScrollToBottom();

            // Start the assistant message for this turn.
            const assistant = this._newMessage('assistant', '');
            assistant.streaming = true;
            store.messages.push(assistant);
            store.current = assistant;
            this._setStatus(store, 'waiting');
            this._current = store.current;   // proxied reference
            this.status = 'waiting';

            const socket = this._socket(id);
            if (!socket || !socket.sendPrompt(content)) {
                console.error('[chat] sendPrompt FAILED -> "Not connected to server."');
                store.error = 'Not connected to server.';
                this.error = store.error;
                this._setStatus(store, 'idle');
                this.status = 'idle';
                assistant.streaming = false;
                store.current = null;
                this._current = null;
            }
            this._forceScrollToBottom();
        },

        // ---------------------------------------------------------------
        // Cancel (Ctrl+C)
        // ---------------------------------------------------------------

        // Abort the in-flight request for the active session.  Sends a
        // `{"type": "cancel"}` message to the server which stops the
        // agentic loop and rolls back the conversation history to the
        // pre-turn checkpoint (removing the user message and any partial
        // assistant response), then locally removes those messages from
        // the UI to stay in sync with the server.
        cancelRequest() {
            const id = this.sessionId;
            if (!id) return;
            const store = this._store(id);

            // Don't cancel if nothing is running.
            if (store.status !== 'waiting' &&
                store.status !== 'streaming' &&
                store.status !== 'tool_running') {
                return;
            }

            // Tell the server to abort the current turn and roll back the
            // history to the checkpoint (before this turn's user message).
            const socket = this._socket(id);
            if (socket) socket.sendCancel();

            // Mirror the server-side rollback in the local UI.
            this._rollbackTurn(store);

            store.error = null;
            this._setStatus(store, 'idle');
            if (store.id === this.sessionId) {
                this._current = null;
                this.status = 'idle';
                this.error = null;
                this._scrollToBottom();
            }
        },

        // ---------------------------------------------------------------
        // Restart (F2)
        // ---------------------------------------------------------------

        // Clear the conversation on both server and client, preserving the
        // system prompt.  Mirrors the shell's F2 key binding.
        restartSession() {
            const id = this.sessionId;
            if (!id) return;

            const store = this._store(id);

            // If a response is in flight, cancel it first (like Ctrl+C) so
            // the server stops the agentic loop before we clear the history.
            if (store.status === 'waiting' ||
                store.status === 'streaming' ||
                store.status === 'tool_running') {
                const cancelSocket = this._socket(id);
                if (cancelSocket) cancelSocket.sendCancel();
                // Finalize the in-flight assistant message locally.
                if (store.current) {
                    store.current.streaming = false;
                    store.current.cancelled = true;
                    store.current = null;
                }
            }

            // Ask the server to clear history (keeps system prompt).
            const socket = this._socket(id);
            if (socket) socket.sendRestart();

            // Reset local UI immediately.
            store.messages.splice(0, store.messages.length);
            store.current = null;
            store.dirty = false;
            store.loaded = true;   // no need to re-fetch empty history
            this._current = null;
            this.error = null;
            store.error = null;
            this._setStatus(store, 'idle');
            this.status = 'idle';
            this.input = '';
            this._autoResize();
            this._forceScrollToBottom();
        },
    },
    // ---- Focused concerns (loaded as separate files before this one) ----
    window.ChatStoreMixin,
    window.ChatEventsMixin,
    window.ChatHistoryMixin,
    window.ChatMessagesMixin,
    window.ChatScrollMixin,
    window.ChatCommandsMixin,
    window.ChatFormatMixin);
}
