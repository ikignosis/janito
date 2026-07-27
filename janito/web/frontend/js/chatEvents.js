// Streamed-event routing for the chat component, as a dispatch table.
//
// `_handleEvent` used to be a giant `switch` (~150 lines). Each case is now a
// handler keyed by `event.type`. Handlers receive a small context object `c`:
//     { comp, event, store, msg, isActive }
// where `msg` is the in-flight assistant message (store.current). Handlers
// may reassign `c.msg`; `_handleEvent` writes it back to `store.current`
// afterwards so 'done'/'cancelled'/'error' can clear it in one place.
//
// `session_start` and `restarted` fire before any assistant message exists,
// so they are handled as early returns (not part of the table).

const CHAT_EVENT_HANDLERS = {
    waiting(c) {
        c.comp._setStatus(c.store, 'waiting');
        if (c.isActive) c.comp.status = 'waiting';
    },

    token(c) {
        c.comp._setStatus(c.store, 'streaming');
        if (c.isActive) c.comp.status = 'streaming';
        c.comp._appendTextPart(c.msg, c.event.content);
        if (c.isActive) c.comp._scrollToBottom();
    },

    reasoning(c) {
        // Reasoning bursts are interleaved with text/tool parts, so each
        // burst separated by other content becomes its own card.
        c.comp._appendReasoningPart(c.msg, c.event.content, true);
        if (c.isActive) c.comp._scrollToBottom();
    },

    tool_call(c) {
        c.comp._setStatus(c.store, 'tool_running');
        if (c.isActive) c.comp.status = 'tool_running';
        const tool = {
            id: c.event.id,
            name: c.event.name,
            args: c.event.args,
            permissions: c.event.permissions || '',
            status: 'running',
            result: null,
            error: null,
            execution_time_ms: null,
            progress: [],
            open: true,
        };
        c.msg.toolCalls.push(tool);            // flat list for id lookup
        c.msg.parts.push({ kind: 'tool', tool });  // same ref, ordered
        if (c.isActive) c.comp._scrollToBottom();
    },

    tool_progress(c) {
        const tc = c.comp._findToolCall(c.msg, c.event.id);
        if (tc) {
            const last = tc.progress[tc.progress.length - 1];
            if (c.event.level === 'output' && last && last.level === 'output') {
                last.message += '\n' + c.event.message;
            } else {
                tc.progress.push({ level: c.event.level, message: c.event.message });
            }
            if (c.isActive) c.comp._scrollToBottom();
        }
    },

    tool_result(c) {
        const tc = c.comp._findToolCall(c.msg, c.event.id);
        if (tc) {
            tc.status = c.event.error ? 'error' : 'done';
            tc.result = c.event.result;
            tc.error = c.event.error;
            tc.execution_time_ms = c.event.execution_time_ms;

            // CreateSVG tool: render the SVG inline as a content card.
            if (!c.event.error && c.event.result
                && c.event.result.content_type === 'svg'
                && c.event.result.svg_text) {
                c.msg.parts.push({ kind: 'svg', svg: c.event.result.svg_text });
            }
        }
        if (c.isActive) c.comp._scrollToBottom();
    },

    usage(c) {
        c.msg.usage = {
            total: c.event.total,
            input: c.event.input,
            output: c.event.output,
            cached: c.event.cached,
        };
        if (c.isActive) {
            window.dispatchEvent(new CustomEvent('janito-usage', { detail: c.msg.usage }));
        }
    },

    done(c) {
        c.msg.streaming = false;
        c.msg.done = true;
        c.comp._setStatus(c.store, 'idle');
        if (c.isActive) {
            c.comp.status = 'idle';
            c.comp._scrollToBottom();
        }
        c.msg = null;
    },

    cancelled(c) {
        // Server confirmed the abort and rolled back the history to the
        // checkpoint. Remove the in-flight assistant message and the user
        // message that started this turn to stay in sync with the server.
        c.comp._rollbackTurn(c.store);
        c.comp._setStatus(c.store, 'idle');
        if (c.isActive) {
            c.comp.status = 'idle';
            c.comp._scrollToBottom();
        }
        c.msg = null;
    },

    error(c) {
        c.store.error = c.event.message;
        // Server rolled back the history to the checkpoint on error.
        c.comp._rollbackTurn(c.store);
        c.comp._setStatus(c.store, 'idle');
        if (c.isActive) {
            c.comp.error = c.event.message;
            c.comp.status = 'idle';
            c.comp._scrollToBottom();
        }
        c.msg = null;

        // Session was lost (e.g. server restarted) — clean up the dead socket
        // and let the sidebar create a fresh session.
        if (/session not found/i.test(c.event.message || '')) {
            console.warn('[chat] session lost on server, recovering…');
            c.comp._releaseSession(c.store.id);
            window.dispatchEvent(new CustomEvent('janito-session-lost', { detail: c.store.id }));
        }
    },
};

window.ChatEventsMixin = {
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
        // preserved. Local UI was already reset in restartSession(); this
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

        // Every other event needs an in-flight assistant message.
        if (!store.current && event.type !== 'error') return;

        const handler = CHAT_EVENT_HANDLERS[event.type];
        if (!handler) return;

        const c = { comp: this, event, store, msg: store.current, isActive };
        handler(c);

        // Write back in case the handler cleared/changed the current message.
        store.current = c.msg;
        if (isActive) this._current = store.current;
    },
};
