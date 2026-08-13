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

    // Format a tool execution duration (in milliseconds) for display.
    // Values below 1000ms are shown as milliseconds; 1000ms and above are
    // converted to seconds (e.g. 1000 -> "1s", 1500 -> "1.5s").
    formatDuration(ms) {
        if (ms === null || ms === undefined) return '';
        if (ms < 1000) return ms + 'ms';
        const seconds = ms / 1000;
        const rounded = Math.round(seconds * 10) / 10;
        return (Number.isInteger(rounded) ? rounded : rounded.toFixed(1)) + 's';
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
            start: '', progress: '\u00b7', output: '', diff: '\u2194', result: '\u2705',
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

    // Extract the filepath for display in a tool card header. Mirrors the
    // backend convention (janito/tooling/used_files.py): the path is shown
    // only when the *first* argument is "filepath" and its value is a
    // non-empty string.
    toolPath(args) {
        if (!args || typeof args !== 'object' || Array.isArray(args)) return '';
        const keys = Object.keys(args);
        if (!keys.length || keys[0] !== 'filepath') return '';
        const path = args.filepath;
        return (typeof path === 'string' && path) ? path : '';
    },

    // Short human-readable summary of a tool call's arguments, rendered in
    // the tool-card header after the tool name. Mirrors the parameters each
    // tool prints via report_start (the operation target shown in the CLI):
    // the header shows the same information the tool announces when it
    // starts. Tools without an entry fall back to the first-argument
    // "filepath" chip (toolPath).
    toolSummary(name, args) {
        if (!name || !args || typeof args !== 'object' || Array.isArray(args)) {
            return this.toolPath(args);
        }
        const s = (v) => (v === null || v === undefined ? '' : String(v));
        const pathList = (v) => {
            if (!Array.isArray(v) || !v.length) return '';
            const shown = v.slice(0, 3).join(', ');
            return v.length > 3 ? `${shown} (+${v.length - 3} more)` : shown;
        };

        switch (name) {
            case 'ReadFile': {
                let sum = s(args.filepath);
                if (args.max_lines !== undefined && args.max_lines !== null) {
                    sum += ` (line ${args.start_line || 1}, max ${args.max_lines} lines)`;
                } else {
                    sum += ` (line ${args.start_line || 1}, until EOF)`;
                }
                return sum;
            }
            case 'CreateFile':
            case 'DeleteFile':
            case 'ReplaceTextInFile':
                return s(args.filepath);
            case 'CreateDirectory':
                return s(args.directory);
            case 'RemoveDirectory':
            case 'ListFiles':
                return s(args.directory) + (args.recursive ? ' (recursive)' : '');
            case 'MoveFile': {
                const pair = [s(args.source), s(args.destination)].filter(Boolean);
                return pair.join(' \u2192 ');
            }
            case 'ReadMultipleFiles':
                return Array.isArray(args.filepath_list)
                    ? `${args.filepath_list.length} files` : '';
            case 'FindFiles': {
                const criteria = [];
                if (args.pattern) criteria.push(`pattern='${args.pattern}'`);
                if (args.file_type) criteria.push(`type=${args.file_type}`);
                const size = [];
                if (args.min_bytes != null) size.push(`>=${args.min_bytes}B`);
                if (args.max_bytes != null) size.push(`<=${args.max_bytes}B`);
                if (size.length) criteria.push(`size ${size.join(',')}`);
                if (args.modified_within_days != null) criteria.push(`modified <${args.modified_within_days}d`);
                if (args.older_than_days != null) criteria.push(`older >${args.older_than_days}d`);
                if (args.exclude) criteria.push(`exclude '${args.exclude}'`);
                const crit = criteria.length ? ` [${criteria.join(', ')}]` : '';
                return pathList(args.paths) + crit;
            }
            case 'SearchText': {
                const parts = [`'${s(args.query)}' in ${pathList(args.paths)}`];
                if (args.exclude) parts.push(`exclude '${args.exclude}'`);
                return parts.join(' ').trim();
            }
            case 'SearchRegex': {
                const parts = [`'${s(args.pattern)}' in ${pathList(args.paths)}`];
                if (args.exclude) parts.push(`exclude '${args.exclude}'`);
                return parts.join(' ').trim();
            }
            case 'ReadEmails':
            case 'CountEmails':
                return s(args.folder);
            case 'DeleteEmails':
            case 'TrashEmail':
                return s(args.folder);
            case 'MoveEmails': {
                const pair = [s(args.source_folder), s(args.target_folder)].filter(Boolean);
                return pair.join(' \u2192 ');
            }
            case 'ListFolders':
                return '';
            // OneDrive tools
            case 'CreateOneDriveFolder':
            case 'DeleteOneDriveFile':
            case 'DownloadOneDriveFile':
            case 'GetOneDriveShareLink':
            case 'UploadOneDriveFile':
                return s(args.path);
            case 'ListOneDriveFiles':
                return s(args.path) || 'root';
            case 'ReadOneDriveFile':
                return s(args.path);
            case 'SearchOneDriveFiles':
                return s(args.query);
            // System / net tools
            case 'OpenBrowser':
            case 'GetUrl':
                return s(args.url);
            case 'WebSearch':
                return s(args.query);
            case 'RunBashCode':
            case 'RunPythonCode':
            case 'RunPowerShellCode':
                return s(args.working_directory);
            case 'RunPythonFile':
                return s(args.file_path);
            case 'RunGitHubCLI':
                return s(args.cmdline).slice(0, 120);
            case 'CreateImage':
                return s(args.size);
            // Skills
            case 'load_skill':
                return s(args.skill_name);
            case 'read_skill_resource': {
                const pair = [s(args.skill_name), s(args.resource_name)].filter(Boolean);
                return pair.join(' / ');
            }
            default:
                return this.toolPath(args);
        }
    },

    // True for the code-execution tools whose `code` argument is rendered
    // as a block at the top of the tool card, visible before the tool
    // actually starts running (before any output streams in).
    isCodeTool(name) {
        return name === 'RunBashCode'
            || name === 'RunPythonCode'
            || name === 'RunPowerShellCode';
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

    // Build the URL used to display an image generated by the CreateImage
    // tool. The backend serves generated temp files under /api/images/<name>.
    // When a bearer token is configured it is passed as a query param so the
    // <img> request is authorised by the TokenAuthMiddleware.
    imageUrl(path) {
        if (!path) return '';
        const name = String(path).split(/[\\/]/).pop();
        let url = '/api/images/' + encodeURIComponent(name);
        const token = window.__JANITO_TOKEN__;
        if (token) url += '?token=' + encodeURIComponent(token);
        return url;
    },

    // Sanitise SVG markup for safe inline rendering.  Uses DOMPurify
    // with the SVG profile when available; falls back to a regex-based
    // strip of <script> and event-handler attributes.
    //
    // When `viewWidth`/`viewHeight` are provided (the CreateSVG tool's
    // view_width/view_height parameters, default 500x500), the requested
    // size is stamped onto the root <svg> element as an inline style so
    // the card renders the graphic at exactly that size (the inline style
    // wins over the .svg-card svg stylesheet rule).
    sanitizeSvg(svgText, viewWidth, viewHeight) {
        if (!svgText) return '';
        let svg;
        if (typeof DOMPurify !== 'undefined') {
            svg = DOMPurify.sanitize(svgText, {
                USE_PROFILES: { svg: true, svgFilters: true },
            });
        } else {
            // Fallback: remove <script> tags and on* event attributes
            svg = svgText
                .replace(/<script[\s\S]*?<\/script>/gi, '')
                .replace(/\son\w+\s*=\s*"[^"]*"/gi, '')
                .replace(/\son\w+\s*=\s*'[^']*'/gi, '');
        }
        if ((viewWidth || viewHeight) && /<svg/i.test(svg)) {
            const w = viewWidth ? `width:${viewWidth}px` : '';
            const h = viewHeight ? `height:${viewHeight}px` : '';
            const style = [w, h].filter(Boolean).join(';');
            svg = svg.replace(/<svg([^>]*)>/i, (m, attrs) => {
                const cleaned = attrs.replace(/\sstyle\s*=\s*"[^"]*"/gi, '');
                return `<svg${cleaned} style="${style}">`;
            });
        }
        return svg;
    },
};
