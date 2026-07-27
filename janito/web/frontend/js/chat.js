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

// Persistent sockets live OUTSIDE the Alpine component so they are never made
// reactive (proxying a live WebSocket is undesirable). Keyed by session id.
const _sessionSockets = new Map();

function chatComponent() {
    return {
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
        // Store management
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
            return _sessionSockets.get(id) || null;
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
            _sessionSockets.set(id, socket);
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

        // If the given session is the active one, mirror its connection state
        // into the top-level `connection` property (and notify the status bar).
        _reflectConnection(id) {
            if (this.sessionId === id) {
                this.connection = this._store(id).connection;
                this._broadcastConn();
            }
        },

        // ---------------------------------------------------------------
        // Status broadcasting (for sidebar indicators)
        // ---------------------------------------------------------------

        // Update a session's status and notify the sidebar so it can show
        // a spinner (processing) or dot (finished) on inactive sessions.
        _setStatus(store, status) {
            if (store.status === status) return;
            store.status = status;
            window.dispatchEvent(new CustomEvent('janito-session-status', {
                detail: { id: store.id, status },
            }));
        },

        // Broadcast the current status of ALL sessions. Called on tab switch
        // so that a session already processing in the background gets its
        // indicator without waiting for the next status change.
        _broadcastAllStatuses() {
            for (const id in this._sessions) {
                const store = this._sessions[id];
                window.dispatchEvent(new CustomEvent('janito-session-status', {
                    detail: { id, status: store.status },
                }));
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
        // ``{"type": "cancel"}`` message to the server which stops the
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

            // Remove the in-flight assistant message and the user message
            // that started this turn, mirroring the server-side rollback.
            if (store.current) {
                const idx = store.messages.indexOf(store.current);
                if (idx !== -1) store.messages.splice(idx, 1);
                store.current = null;
            }
            // Remove the last user message (the one that triggered this turn).
            for (let i = store.messages.length - 1; i >= 0; i--) {
                if (store.messages[i].role === 'user') {
                    store.messages.splice(i, 1);
                    break;
                }
            }

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

        // ---------------------------------------------------------------
        // Event routing
        // ---------------------------------------------------------------

        // Apply a streamed event to a specific session's store. Only mutates
        // the visible projection when that session is the active tab.
        _handleEvent(event, store) {
            const isActive = (store.id === this.sessionId);

            // Server greets us on connect with a tools summary. This arrives
            // before any assistant message exists, so handle it up front.
            if (event.type === 'session_start') {
                store.toolsSummary = {
                    active: event.active_tools || 0,
                    skipped: event.skipped_tools || 0,
                    skippedList: event.skipped || {},
                };
                if (isActive) this.toolsSummary = store.toolsSummary;
                return;
            }

            // Server confirmed the restart — history cleared, system prompt
            // preserved.  Local UI was already reset in restartSession(); this
            // just serves as an acknowledgement.
            if (event.type === 'restarted') {
                store.current = null;
                store.dirty = false;
                store.loaded = true;
                this._setStatus(store, 'idle');
                if (isActive) {
                    this._current = null;
                    this.status = 'idle';
                    this._forceScrollToBottom();
                }
                return;
            }

            const m = store.current;   // proxied -> mutations are reactive
            if (!m && event.type !== 'error') return;

            switch (event.type) {
                case 'waiting':
                    this._setStatus(store, 'waiting');
                    if (isActive) this.status = 'waiting';
                    break;

                case 'token':
                    this._setStatus(store, 'streaming');
                    if (isActive) this.status = 'streaming';
                    this._appendTextPart(m, event.content);
                    if (isActive) this._scrollToBottom();
                    break;

                case 'reasoning':
                    // Reasoning bursts are interleaved with text/tool parts, so
                    // each burst separated by other content becomes its own card.
                    this._appendReasoningPart(m, event.content, true);
                    if (isActive) this._scrollToBottom();
                    break;

                case 'tool_call': {
                    this._setStatus(store, 'tool_running');
                    if (isActive) this.status = 'tool_running';
                    const tool = {
                        id: event.id,
                        name: event.name,
                        args: event.args,
                        permissions: event.permissions || '',
                        status: 'running',
                        result: null,
                        error: null,
                        execution_time_ms: null,
                        progress: [],
                        open: true,
                    };
                    m.toolCalls.push(tool);            // flat list for id lookup
                    m.parts.push({ kind: 'tool', tool });  // same ref, ordered
                    if (isActive) this._scrollToBottom();
                    break;
                }

                case 'tool_progress': {
                    const tc = this._findToolCall(m, event.id);
                    if (tc) {
                        const last = tc.progress[tc.progress.length - 1];
                        if (event.level === 'output' && last && last.level === 'output') {
                            last.message += '\n' + event.message;
                        } else {
                            tc.progress.push({ level: event.level, message: event.message });
                        }
                        if (isActive) this._scrollToBottom();
                    }
                    break;
                }

                case 'tool_result': {
                    const tc = this._findToolCall(m, event.id);
                    if (tc) {
                        tc.status = event.error ? 'error' : 'done';
                        tc.result = event.result;
                        tc.error = event.error;
                        tc.execution_time_ms = event.execution_time_ms;

                        // CreateSVG tool: render the SVG inline as a content card.
                        if (!event.error && event.result
                            && event.result.content_type === 'svg'
                            && event.result.svg_text) {
                            m.parts.push({ kind: 'svg', svg: event.result.svg_text });
                        }
                    }
                    if (isActive) this._scrollToBottom();
                    break;
                }

                case 'usage':
                    m.usage = {
                        total: event.total,
                        input: event.input,
                        output: event.output,
                        cached: event.cached,
                    };
                    if (isActive) {
                        window.dispatchEvent(new CustomEvent('janito-usage', { detail: m.usage }));
                    }
                    break;

                case 'done':
                    m.streaming = false;
                    m.done = true;
                    store.current = null;
                    this._setStatus(store, 'idle');
                    if (isActive) {
                        this._current = null;
                        this.status = 'idle';
                        this._scrollToBottom();
                    }
                    break;

                case 'cancelled':
                    // Server confirmed the abort and rolled back the history
                    // to the checkpoint.  Remove the in-flight assistant
                    // message and the user message that started this turn
                    // from the local UI so it stays in sync with the server.
                    if (m) {
                        const idx = store.messages.indexOf(m);
                        if (idx !== -1) store.messages.splice(idx, 1);
                    }
                    // Remove the last user message (the one that triggered
                    // this turn).
                    for (let i = store.messages.length - 1; i >= 0; i--) {
                        if (store.messages[i].role === 'user') {
                            store.messages.splice(i, 1);
                            break;
                        }
                    }
                    store.current = null;
                    this._setStatus(store, 'idle');
                    if (isActive) {
                        this._current = null;
                        this.status = 'idle';
                        this._scrollToBottom();
                    }
                    break;

                case 'error':
                    store.error = event.message;
                    // Server rolled back the history to the checkpoint on
                    // error.  Remove the in-flight assistant message and the
                    // user message that started this turn from the local UI.
                    if (m) {
                        const idx = store.messages.indexOf(m);
                        if (idx !== -1) store.messages.splice(idx, 1);
                    }
                    for (let i = store.messages.length - 1; i >= 0; i--) {
                        if (store.messages[i].role === 'user') {
                            store.messages.splice(i, 1);
                            break;
                        }
                    }
                    store.current = null;
                    this._setStatus(store, 'idle');
                    if (isActive) {
                        this.error = event.message;
                        this._current = null;
                        this.status = 'idle';
                        this._scrollToBottom();
                    }
                    // Session was lost (e.g. server restarted) — clean up the
                    // dead socket and let the sidebar create a fresh session.
                    if (/session not found/i.test(event.message || '')) {
                        console.warn('[chat] session lost on server, recovering…');
                        this._releaseSession(store.id);
                        window.dispatchEvent(new CustomEvent('janito-session-lost', { detail: store.id }));
                    }
                    break;
            }
        },

        _findToolCall(msg, id) {
            return msg.toolCalls.find(tc => tc.id === id);
        },

        // ---------------------------------------------------------------
        // Session deletion
        // ---------------------------------------------------------------

        // Release a session's persistent socket and store. Safe to call for a
        // session that is active, background, or unknown.
        _releaseSession(id) {
            const socket = this._socket(id);
            if (socket) {
                socket.close();
                _sessionSockets.delete(id);
            }
            delete this._sessions[id];
        },

        // The active session was deleted: free its resources and clear the view.
        clearActive() {
            if (this.sessionId) this._releaseSession(this.sessionId);
            this.sessionId = null;
            this.messages = [];
            this.status = 'idle';
            this.connection = 'disconnected';
            this.error = null;
            this._current = null;
            this.toolsSummary = null;
            this._broadcastConn();
        },

        // ---------------------------------------------------------------
        // History reconstruction
        // ---------------------------------------------------------------

        // Convert a session's stored message history into UI message objects.
        //
        // The backend stores one entry per agentic-loop turn, so a single user
        // prompt can produce: assistant(tool_calls) -> tool(result) -> ... ->
        // assistant(final text). During live streaming all of those render into
        // ONE assistant bubble (chat.js reuses `current` until `done`). To make
        // a reloaded tab look identical, we merge every turn between two user
        // messages into a single assistant UI message, reconstructing the
        // ordered interleaving of reasoning / text / tool-call parts (each
        // reasoning burst becomes its own card, matching live streaming) and
        // attaching tool results to their cards instead of dropping them.
        _historyToUi(stored) {
            const ui = [];
            let current = null;   // assistant UI message for the current turn
            for (const msg of stored) {
                if (msg.role === 'system') {
                    continue;
                } else if (msg.role === 'user') {
                    current = null;   // a new user prompt starts a fresh turn
                    ui.push(this._newMessage('user', msg.content));
                } else if (msg.role === 'assistant') {
                    if (!current || current.role !== 'assistant') {
                        current = this._newMessage('assistant', '');
                        ui.push(current);
                    }
                    // Order of parts within one assistant turn mirrors the
                    // model's actual output: reasoning -> content -> tool calls.
                    // Because a different part kind always intervenes between
                    // turns, each reasoning burst ends up as its own card.
                    if (msg.reasoning_content) {
                        this._appendReasoningPart(current, msg.reasoning_content, false);
                    }
                    if (msg.content) {
                        this._appendTextPart(current, msg.content, '\n\n');
                    }
                    if (Array.isArray(msg.tool_calls)) {
                        for (const tc of msg.tool_calls) {
                            let args = {};
                            try { args = JSON.parse(tc.function.arguments); } catch (e) { /* keep {} */ }
                            const tool = {
                                id: tc.id,
                                name: tc.function.name,
                                args,
                                permissions: '',
                                status: 'done',
                                result: null,
                                error: null,
                                execution_time_ms: null,
                                progress: [],
                                open: false,
                            };
                            current.toolCalls.push(tool);
                            current.parts.push({ kind: 'tool', tool });
                        }
                    }
                    current.done = true;
                } else if (msg.role === 'tool') {
                    // Attach the tool result to its matching tool-call card.
                    if (current) {
                        const tc = current.toolCalls.find(t => t.id === msg.tool_call_id);
                        if (tc) {
                            let result = msg.content;
                            try { result = JSON.parse(msg.content); } catch (e) { /* keep raw string */ }
                            if (result && typeof result === 'object' && result.success === false && result.error) {
                                tc.status = 'error';
                                tc.error = result.error;
                            }
                            tc.result = result;

                            // Reconstruct SVG part from CreateSVG tool result.
                            if (result && typeof result === 'object'
                                && result.content_type === 'svg'
                                && result.svg_text) {
                                current.parts.push({ kind: 'svg', svg: result.svg_text });
                            }
                        }
                    }
                }
            }
            return ui;
        },

        // ---------------------------------------------------------------
        // Message part builders (ordered reasoning / text / tool cards)
        // ---------------------------------------------------------------

        // Append streamed/history text. Consecutive text merges into the last
        // text part; `joiner` separates history turns ('\n\n'), streaming uses ''.
        _appendTextPart(m, text, joiner = '') {
            const last = m.parts[m.parts.length - 1];
            if (last && last.kind === 'text') {
                last.text += joiner + text;
            } else {
                m.parts.push({ kind: 'text', text });
            }
            m.rawContent = (m.rawContent ? m.rawContent + joiner : '') + text;
            m.content = m.rawContent;
        },

        // Append reasoning. `open=true` for live streaming (card starts expanded),
        // `open=false` for history (collapsed). Reasoning that arrives right
        // after reasoning continues the same card; any other part kind in
        // between starts a NEW reasoning card -> multiple interleaved cards.
        _appendReasoningPart(m, text, open) {
            const last = m.parts[m.parts.length - 1];
            if (last && last.kind === 'reasoning') {
                last.text += text;
            } else {
                m.parts.push({ kind: 'reasoning', text, open });
            }
        },

        _newMessage(role, content = '') {
            const msg = {
                role,
                content: content,
                rawContent: content,
                parts: [],           // ordered: {kind:'reasoning'|'text'|'tool', ...}
                toolCalls: [],       // flat list (for id lookup on tool_* events)
                usage: null,
                streaming: false,
                done: role === 'user',
            };
            // Assistant text parts are added via _appendTextPart as they stream.
            // (User messages render through a dedicated block, not `parts`, so
            //  we never seed a part for them here to avoid double-rendering.)
            return msg;
        },

        // ---------------------------------------------------------------
        // Input + UI helpers
        // ---------------------------------------------------------------

        // Keyboard: Enter to send, Shift+Enter for newline, F2 to restart,
        // Ctrl+C to cancel the current request.
        onKeydown(e) {
            if (e.key === 'F2') {
                e.preventDefault();
                this.restartSession();
                return;
            }
            if ((e.ctrlKey || e.metaKey) && e.key === 'c') {
                // Only cancel if a request is in flight; otherwise let the
                // browser do its default (copy selected text / clear input).
                if (this.status === 'waiting' ||
                    this.status === 'streaming' ||
                    this.status === 'tool_running') {
                    e.preventDefault();
                    this.cancelRequest();
                }
                return;
            }
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendPrompt();
            }
        },

        _autoResize() {
            this.$nextTick(() => {
                const el = this.$refs.input;
                if (el) {
                    el.style.height = 'auto';
                    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
                }
            });
        },

        _updateFollowBottom() {
            const el = this.$refs.chatArea;
            if (!el) return;
            const dist = el.scrollHeight - el.scrollTop - el.clientHeight;
            this._followBottom = dist <= this._scrollThreshold;
        },

        // Snap to the bottom unconditionally (tab switch, history load, sending
        // a message, "jump to latest"). Also re-arms the auto-follow state so
        // subsequent streaming keeps the view pinned.
        _forceScrollToBottom() {
            this._followBottom = true;
            this.$nextTick(() => {
                const el = this.$refs.chatArea;
                if (el) el.scrollTop = el.scrollHeight;
            });
        },

        // Follow new content ONLY if the user was already at (or near) the
        // bottom. If they scrolled up to read, their position is preserved
        // ("scroll lock").
        _scrollToBottom() {
            if (!this._followBottom) return;
            this.$nextTick(() => {
                const el = this.$refs.chatArea;
                if (el) el.scrollTop = el.scrollHeight;
            });
        },

        _broadcastConn() {
            window.dispatchEvent(new CustomEvent('janito-connection', { detail: this.connection }));
        },

        // ---------------------------------------------------------------
        // Format helpers
        // ---------------------------------------------------------------

        formatTokens(n) {
            if (n === null || n === undefined) return '';
            if (n >= 1000000) return (n / 1000000).toFixed(1).replace(/\.0$/, '') + 'm';
            if (n >= 1000) return (n / 1000).toFixed(1).replace(/\.0$/, '') + 'k';
            return String(n);
        },

        permLabel(perms) {
            if (!perms) return '';
            if (perms.includes('x')) return 'exec';
            if (perms.includes('w')) return 'write';
            if (perms.includes('r')) return 'read';
            return '';
        },

        permClass(perms) {
            const label = this.permLabel(perms);
            return label || 'read';
        },

        levelIcon(level) {
            const icons = {
                start: '', progress: '\u00b7', output: '', result: '\u2705',
                error: '\u274c', warning: '\u26a0\ufe0f', info: '\u2139\ufe0f',
            };
            return level in icons ? icons[level] : '\u00b7';
        },

        statusLabel(status) {
            return { running: 'Running', done: 'Done', error: 'Error' }[status] || status;
        },

        toolArgsStr(args) {
            try { return JSON.stringify(args, null, 2); }
            catch (e) { return String(args); }
        },

        toolResultStr(result) {
            if (result === null || result === undefined) return '';
            if (typeof result === 'string') return result;
            try { return JSON.stringify(result, null, 2); }
            catch (e) { return String(result); }
        },

        renderMarkdown(text) {
            return window.JanitoMarkdown ? window.JanitoMarkdown.render(text || '') : (text || '');
        },

        // Sanitise SVG markup for safe inline rendering.  Uses DOMPurify
        // with the SVG profile when available; falls back to a regex-based
        // strip of <script> and event-handler attributes.
        sanitizeSvg(svgText) {
            if (!svgText) return '';
            if (typeof DOMPurify !== 'undefined') {
                return DOMPurify.sanitize(svgText, {
                    USE_PROFILES: { svg: true, svgFilters: true },
                });
            }
            // Fallback: remove <script> tags and on* event attributes
            return svgText
                .replace(/<script[\s\S]*?<\/script>/gi, '')
                .replace(/\son\w+\s*=\s*"[^"]*"/gi, '')
                .replace(/\son\w+\s*=\s*'[^']*'/gi, '');
        },
    };
}
