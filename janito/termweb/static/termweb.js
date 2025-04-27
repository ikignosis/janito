// Directory/File browser logic for explorer with right-side preview and URL sync (using /path)
let explorerView = localStorage.getItem('explorerView') || 'list';
let currentExplorerPath = '.';

function getParentPath(path) {
    // Normalize slashes
    path = (path || '').replace(/\\/g, '/').replace(/^\/+|\/+$/g, '');
    if (!path || path === '.' || path === '') return '.';
    const parts = path.split('/');
    if (parts.length <= 1) return '.';
    parts.pop();
    const parent = parts.join('/');
    return parent === '' ? '.' : parent;
}

function setExplorerView(view) {
    explorerView = view;
    localStorage.setItem('explorerView', view);
    document.getElementById('view-list').classList.toggle('active', view === 'list');
    document.getElementById('view-icons').classList.toggle('active', view === 'icons');
}

function normalizeExplorerPath(path) {
    if (!path || path === '/' || path === '' || path === '.') return '.';
    return path.replace(/^\/+|\/+$/g, '');
}

function updateExplorerUrl(path, push=true) {
    let url = '/';
    if (path && path !== '.' && path !== '/') {
        url = '/' + path.replace(/^\/+|\/+$/g, '');
    }
    if (push) {
        window.history.pushState({ explorerPath: path }, '', url);
    }
}

function renderExplorer(path, pushUrl=true) {
    currentExplorerPath = normalizeExplorerPath(path);
    fetch(`/api/explorer/${encodeURIComponent(currentExplorerPath)}`)
        .then(resp => resp.json())
        .then(data => {
            const main = document.getElementById('explorer-main');
            if (!main) return;
            if (data.error) {
                main.innerHTML = `<div class='error'>${data.error}</div>`;
                return;
            }
            if (data.type === 'dir') {
                let html = `<h3>Directory: ${data.path}</h3>`;
                if (explorerView === 'list') {
                    html += `<ul class='explorer-list'>`;
                    if (data.path !== '.') {
                        const parent = getParentPath(data.path);
                        html += `<li><a href='#' data-path='${parent}' class='explorer-link'><span class='explorer-entry'><span class='explorer-icon'>\u2b06\ufe0f</span><span class='explorer-name'>(.. parent)</span></span></a></li>`;
                    }
                    for (const entry of data.entries) {
                        const entryPath = data.path === '.' ? entry.name : data.path + '/' + entry.name;
                        if (entry.is_dir) {
                            html += `<li><a href='#' data-path='${entryPath}' class='explorer-link'><span class='explorer-entry'><span class='explorer-icon'>\ud83d\udcc1</span><span class='explorer-name'>${entry.name}</span></span></a></li>`;
                        } else {
                            html += `<li><a href='#' data-path='${entryPath}' class='explorer-link file-link'><span class='explorer-entry'><span class='explorer-icon'>\ud83d\udcc4</span><span class='explorer-name'>${entry.name}</span></span></a></li>`;
                        }
                    }
                    html += '</ul>';
                } else {
                    html += `<div class='explorer-icons'>`;
                    if (data.path !== '.') {
                        const parent = getParentPath(data.path);
                        html += `<div class='explorer-icon'><a href='#' data-path='${parent}' class='explorer-link' title='Parent'>(..)</a></div>`;
                    }
                    for (const entry of data.entries) {
                        const entryPath = data.path === '.' ? entry.name : data.path + '/' + entry.name;
                        if (entry.is_dir) {
                            html += `<div class='explorer-icon'><a href='#' data-path='${entryPath}' class='explorer-link' title='${entry.name}'>\ud83d\udcc1<br>${entry.name}</a></div>`;
                        } else {
                            html += `<div class='explorer-icon'><a href='#' data-path='${entryPath}' class='explorer-link file-link' title='${entry.name}'>\ud83d\udcc4<br>${entry.name}</a></div>`;
                        }
                    }
                    html += '</div>';
                }
                main.innerHTML = html;
                // Clear preview panel when changing directories
                const preview = document.getElementById('explorer-preview');
                if (preview) preview.innerHTML = '';
                if (pushUrl) updateExplorerUrl(currentExplorerPath, true);
            }
            // Attach click handlers
            document.querySelectorAll('.explorer-link').forEach(link => {
                link.onclick = function(e) {
                    e.preventDefault();
                    const p = this.getAttribute('data-path');
                    // If file, show preview; if dir, update explorer
                    if (this.classList.contains('file-link')) {
                        const preview = document.getElementById('explorer-preview');
                        if (preview) {
                            preview.innerHTML = `<div class='spinner' style='display:inline-block;vertical-align:middle;'></div> <span style='vertical-align:middle;'>Loading file...</span>`;
                        }
                        fetch(`/api/explorer/${encodeURIComponent(p)}`)
                            .then(resp => resp.json())
                            .then(fileData => {
                                if (preview && fileData.type === 'file') {
                                    if (window.renderCodePreview) {
                                        preview.innerHTML = `<h3>File: ${fileData.path}</h3><div id='explorer-codemirror-preview'></div>`;
                                        window.renderCodePreview(document.getElementById('explorer-codemirror-preview'), fileData.content, 'python');
                                    } else {
                                        preview.innerHTML = `<h3>File: ${fileData.path}</h3><pre class='explorer-file'>${escapeHtml(fileData.content)}</pre>`;
                                    }
                                }
                            });
                    } else {
                        renderExplorer(p, true);
                    }
                };
            });
        });
}

function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/[&<>"']/g, function (c) {
        return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
    });
}

// Patch: Use CodeMirror for explorer preview in read-only mode
window.renderCodePreview = function(container, content, mode) {
    if (!container) return;
    container.innerHTML = '';
    try {
        var textarea = document.createElement('textarea');
        textarea.value = (typeof content === 'string') ? content : '';
        container.appendChild(textarea);
        if (window.CodeMirror && container.offsetParent !== null) {
            var editor = CodeMirror.fromTextArea(textarea, {
                lineNumbers: true,
                mode: mode || 'python',
                theme: (document.body.classList.contains('light-theme') ? 'default' : 'dracula'),
                readOnly: true,
                indentUnit: 4,
                tabSize: 4,
            });
            editor.setSize('100%', 'calc(60vh)');
            return editor;
        } else {
            container.innerHTML = '<pre>' + (content ? String(content) : '') + '</pre>';
        }
    } catch (e) {
        container.innerHTML = '<pre>' + (content ? String(content) : '') + '</pre>';
    }
}

// Theme switcher logic
function setTheme(dark) {
    if (dark) {
        document.body.classList.add('dark-theme');
        document.body.classList.remove('light-theme');
        localStorage.setItem('theme', 'dark');
        document.getElementById('theme-switcher').textContent = 'Switch to Light Theme';
    } else {
        document.body.classList.remove('dark-theme');
        document.body.classList.add('light-theme');
        localStorage.setItem('theme', 'light');
        document.getElementById('theme-switcher').textContent = 'Switch to Dark Theme';
    }
}
document.addEventListener('DOMContentLoaded', function() {
    // Initial theme
    var theme = localStorage.getItem('theme') || 'dark';
    setTheme(theme === 'dark');
    document.getElementById('theme-switcher').onclick = function() {
        setTheme(document.body.classList.contains('light-theme'));
    };
    renderExplorer('.')
    setExplorerView(localStorage.getItem('explorerView') || 'list');
    document.getElementById('view-list').onclick = function() {
        setExplorerView('list');
        renderExplorer('.')
    };
    document.getElementById('view-icons').onclick = function() {
        setExplorerView('icons');
        renderExplorer('.')
    };
});

window.renderExplorer = renderExplorer;
window.setExplorerView = setExplorerView;
