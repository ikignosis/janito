// History reconstruction: convert a session's stored message history into
// UI message objects.
//
// The backend stores one entry per agentic-loop turn, so a single user prompt
// can produce: assistant(tool_calls) -> tool(result) -> ... ->
// assistant(final text). During live streaming all of those render into ONE
// assistant bubble (chat.js reuses `current` until `done`). To make a reloaded
// tab look identical, this merges every turn between two user messages into a
// single assistant UI message, reconstructing the ordered interleaving of
// reasoning / text / tool-call parts (each reasoning burst becomes its own
// card, matching live streaming) and attaching tool results to their cards
// instead of dropping them.

window.ChatHistoryMixin = {
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
                // Order of parts within one assistant turn mirrors the model's
                // actual output: reasoning -> content -> tool calls. Because a
                // different part kind always intervenes between turns, each
                // reasoning burst ends up as its own card. Cards start
                // expanded (`open=true`) so loaded thinking is visible, just
                // like live streaming.
                if (msg.reasoning_content) {
                    this._appendReasoningPart(current, msg.reasoning_content, true);
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

                        // Reconstruct image part from CreateImage tool result.
                        if (result && typeof result === 'object'
                            && result.content_type === 'image'
                            && result.image_path) {
                            current.parts.push({ kind: 'image', path: result.image_path });
                        }
                    }
                }
            }
        }
        return ui;
    },
};
