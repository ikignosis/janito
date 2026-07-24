// Chat Alpine.js component — messages, streaming, input, tool monitor.
//
// UI state machine:
//   idle -> [send prompt] -> waiting -> [first token] -> streaming
//        -> [tool_call] -> tool_running -> [tool_result] -> waiting -> streaming
//        -> [done] -> idle

function chatComponent() {
    return {
        // Reactive state
        messages: [],            // UI message objects (see below)
        input: '',
        status: 'idle',          // idle | waiting | streaming | tool_running
        connection: 'disconnected',  // disconnected | connecting | connected
        error: null,
        socket: null,
        config: {},
        sessionId: null,

        // Track the currently-streaming assistant message
        _current: null,

        init() {
            // Listen for session selection from sessions.js
            window.addEventListener('janito-open-session', (e) => {
                this.connectToSession(e.detail);
            });
            // Listen for session clear (deleted active session)
            window.addEventListener('janito-clear-session', () => {
                if (this.socket) this.socket.close();
                this.socket = null;
                this.sessionId = null;
                this.messages = [];
                this.status = 'idle';
                this.connection = 'disconnected';
                this._broadcastConn();
            });
        },

        async connectToSession(sessionId) {
            if (this.socket) this.socket.close();
            this.sessionId = sessionId;
            this.messages = [];
            this.status = 'idle';
            this.error = null;
            this.connection = 'connecting';

            // Load existing history
            try {
                const session = await Api.getSession(sessionId);
                this.messages = this._historyToUi(session.messages || []);
            } catch (e) {
                console.error('Failed to load session history:', e);
            }

            this.socket = new ChatSocket(sessionId, {
                onOpen: () => { this.connection = 'connected'; this._broadcastConn(); },
                onClose: () => {
                    this.connection = this.socket && this.socket.reconnectAttempts < this.socket.maxReconnectAttempts
                        ? 'connecting' : 'disconnected';
                    this._broadcastConn();
                },
                onEvent: (event) => this._handleEvent(event),
            });
            this.socket.connect();
            this._broadcastConn();
            this._scrollToBottom();
        },

        _broadcastConn() {
            window.dispatchEvent(new CustomEvent('janito-connection', { detail: this.connection }));
        },

        // Convert stored message history into UI message objects
        _historyToUi(stored) {
            const ui = [];
            for (const msg of stored) {
                if (msg.role === 'system') continue;
                if (msg.role === 'user') {
                    ui.push(this._newMessage('user', msg.content));
                } else if (msg.role === 'assistant') {
                    const m = this._newMessage('assistant', msg.content || '');
                    m.rawContent = msg.content || '';
                    m.reasoning = msg.reasoning_content || '';
                    m.done = true;
                    ui.push(m);
                }
                // tool messages are not shown standalone in history
            }
            return ui;
        },

        _newMessage(role, content = '') {
            return {
                role,
                content: content,
                rawContent: content,
                reasoning: '',
                reasoningOpen: false,
                toolCalls: [],
                usage: null,
                streaming: false,
                done: role === 'user',
            };
        },

        sendPrompt() {
            const content = this.input.trim();
            if (!content) return;
            if (this.status === 'waiting' || this.status === 'streaming') return;

            this.error = null;
            // Add user message
            this.messages.push(this._newMessage('user', content));
            this.input = '';
            this._autoResize();
            this._scrollToBottom();

            // Start assistant message
            this._current = this._newMessage('assistant', '');
            this._current.streaming = true;
            this.messages.push(this._current);
            this.status = 'waiting';

            if (!this.socket || !this.socket.sendPrompt(content)) {
                this.error = 'Not connected to server.';
                this.status = 'idle';
                this._current.streaming = false;
            }
            this._scrollToBottom();
        },

        _handleEvent(event) {
            const m = this._current;
            if (!m && event.type !== 'error') return;

            switch (event.type) {
                case 'waiting':
                    this.status = 'waiting';
                    break;

                case 'token':
                    this.status = 'streaming';
                    m.rawContent += event.content;
                    m.content = m.rawContent;   // markdown re-rendered in template
                    this._scrollToBottom();
                    break;

                case 'reasoning':
                    m.reasoning += event.content;
                    m.reasoningOpen = true;
                    this._scrollToBottom();
                    break;

                case 'tool_call':
                    this.status = 'tool_running';
                    m.toolCalls.push({
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
                    });
                    this._scrollToBottom();
                    break;

                case 'tool_progress': {
                    const tc = this._findToolCall(m, event.id);
                    if (tc) {
                        // Aggregate consecutive "output" lines into a single block
                        const last = tc.progress[tc.progress.length - 1];
                        if (event.level === 'output' && last && last.level === 'output') {
                            last.message += '\n' + event.message;
                        } else {
                            tc.progress.push({ level: event.level, message: event.message });
                        }
                        this._scrollToBottom();
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
                    }
                    this._scrollToBottom();
                    break;
                }

                case 'usage':
                    m.usage = {
                        total: event.total,
                        input: event.input,
                        output: event.output,
                        cached: event.cached,
                    };
                    window.dispatchEvent(new CustomEvent('janito-usage', { detail: m.usage }));
                    break;

                case 'done':
                    m.streaming = false;
                    m.done = true;
                    this._current = null;
                    this.status = 'idle';
                    this._scrollToBottom();
                    break;

                case 'error':
                    this.error = event.message;
                    if (m) { m.streaming = false; }
                    this._current = null;
                    this.status = 'idle';
                    this._scrollToBottom();
                    break;
            }
        },

        _findToolCall(msg, id) {
            return msg.toolCalls.find(tc => tc.id === id);
        },

        // Keyboard: Enter to send, Shift+Enter for newline
        onKeydown(e) {
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

        _scrollToBottom() {
            this.$nextTick(() => {
                const el = this.$refs.chatArea;
                if (el) el.scrollTop = el.scrollHeight;
            });
        },

        // Format helpers
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
                start: '▶', progress: '·', output: '', result: '✅',
                error: '❌', warning: '⚠️', info: 'ℹ️',
            };
            return icons[level] || '·';
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
    };
}
