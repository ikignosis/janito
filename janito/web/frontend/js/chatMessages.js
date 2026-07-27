// UI message builders (ordered reasoning / text / tool cards).
// Folded into the Alpine component via Object.assign in chat.js.

window.ChatMessagesMixin = {
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

    _findToolCall(msg, id) {
        return msg.toolCalls.find(tc => tc.id === id);
    },
};
