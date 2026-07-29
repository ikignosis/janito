// Client-side slash commands for the web chat.
//
// The CLI shell intercepts slash commands (`/tools`, `/help`, …) in the
// interactive shell. The web chat has no equivalent today: anything typed
// into the input box is shipped to the model over the WebSocket. This mixin
// adds a small dispatch table for commands that can be answered entirely on
// the client, without spending tokens or touching the server's conversation
// history. Commands return `true` when handled so the caller knows to skip
// the normal prompt path.
//
// Currently implemented:
//   /tools  — list all loaded built-in + MCP tools in a formatted panel
//
// The output is rendered as a special message part (kind: 'tools') so it
// lives inside the message stream like any other assistant content but is
// styled as a distinct, card-based panel (see css/tools.css and the
// `part.kind === 'tools'` template block in index.html).
//
// Folded into the Alpine component via Object.assign in chat.js.

// Fetch the tool data from the backend and shape it for the template.
async function _fetchToolsListing() {
    // Built-in tools and skipped-tools reasons.
    let builtin = [];
    let skipped = {};
    try {
        const data = await Api.getTools();
        builtin = (data.tools || []).map(t => ({
            name: t.name,
            description: t.description || '',
            permissions: t.permissions || '',
        }));
    } catch (e) {
        console.warn('[chat] /tools: failed to load built-in tools', e);
    }
    try {
        const data = await Api.getSkippedTools();
        skipped = data.skipped || {};
    } catch (e) {
        console.warn('[chat] /tools: failed to load skipped tools', e);
    }

    // MCP tools come back as raw function-calling schemas:
    //   { type: "function", function: { name, description, ... } }
    let mcp = [];
    try {
        const data = await Api.getMcpTools();
        mcp = (data.tools || []).map(s => {
            const fn = s.function || s || {};
            return { name: fn.name || s.name || '', description: fn.description || '' };
        }).filter(t => t.name);
    } catch (e) {
        console.warn('[chat] /tools: failed to load MCP tools', e);
    }

    const byName = (a, b) => a.name.localeCompare(b.name);
    return {
        builtin: builtin.sort(byName),
        mcp: mcp.sort(byName),
        skipped: skipped,
        total: builtin.length + mcp.length,
    };
}

window.ChatCommandsMixin = {
    // Handle a client-side slash command. Returns true if the command was
    // recognised and handled (caller should NOT send it to the model).
    _handleSlashCommand(content, store) {
        const cmd = content.toLowerCase();

        if (cmd === '/tools') {
            this._runToolsCommand(store);
            return true;
        }

        // Unrecognised slash command — fall through to the model.
        return false;
    },

    // Render the /tools listing as an assistant message with a 'tools' part.
    async _runToolsCommand(store) {
        const isActive = (store.id === this.sessionId);

        // Echo the user's command as a normal user message.
        store.messages.push(this._newMessage('user', '/tools'));
        store.dirty = true;
        if (isActive) this._forceScrollToBottom();

        // Build the assistant message that will host the tools panel.
        const assistant = this._newMessage('assistant', '');
        const part = { kind: 'tools', tools: null, loading: true, error: null };
        assistant.parts.push(part);
        assistant.done = true;
        store.messages.push(assistant);
        if (isActive) this._forceScrollToBottom();

        try {
            part.tools = await _fetchToolsListing();
            part.loading = false;
        } catch (e) {
            part.loading = false;
            part.error = 'Failed to load tools: ' + e.message;
        }
        if (isActive) this._forceScrollToBottom();
    },
};
