// Pure formatting / rendering helpers for the chat component.
// No `this` dependencies beyond other component helpers — folded into the
// Alpine component via Object.assign in chat.js.

window.ChatFormatMixin = {
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
