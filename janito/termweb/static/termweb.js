// Directory/File browser logic for explorer with view toggle
let explorerView = localStorage.getItem('explorerView') || 'list';

function setExplorerView(view) {
    explorerView = view;
    localStorage.setItem('explorerView', view);
    document.getElementById('view-list').classList.toggle('active', view === 'list');
    document.getElementById('view-icons').classList.toggle('active', view === 'icons');
}

function renderExplorer(path) {
    fetch(`/api/explorer/${encodeURIComponent(path || ".")}`)
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
                        const parent = data.path
                            .replace(/\\|\//g, '/')
                            .replace(/\/[^\/]+$/, '')
                            .replace(/\//g, '/');
                        html += `<li><a href='#' data-path='${parent || '.'}' class='explorer-link'>(.. parent)</a></li>`;
                    }
                    for (const entry of data.entries) {
                        const entryPath = data.path === '.' ? entry.name : data.path + '/' + entry.name;
                        if (entry.is_dir) {
                            html += `<li><a href='#' data-path='${entryPath}' class='explorer-link'>📁 ${entry.name}</a></li>`;
                        } else {
                            html += `<li><a href='#' data-path='${entryPath}' class='explorer-link file-link'>📄 ${entry.name}</a></li>`;
                        }
                    }
                    html += '</ul>';
                } else {
                    html += `<div class='explorer-icons'>`;
                    if (data.path !== '.') {
                        const parent = data.path
                            .replace(/\\|\//g, '/')
                            .replace(/\/[^\/]+$/, '')
                            .replace(/\//g, '/');
                        html += `<div class='explorer-icon'><a href='#' data-path='${parent || '.'}' class='explorer-link' title='Parent'>(..)</a></div>`;
                    }
                    for (const entry of data.entries) {
                        const entryPath = data.path === '.' ? entry.name : data.path + '/' + entry.name;
                        if (entry.is_dir) {
                            html += `<div class='explorer-icon'><a href='#' data-path='${entryPath}' class='explorer-link' title='${entry.name}'>📁<br>${entry.name}</a></div>`;
                        } else {
                            html += `<div class='explorer-icon'><a href='#' data-path='${entryPath}' class='explorer-link file-link' title='${entry.name}'>📄<br>${entry.name}</a></div>`;
                        }
                    }
                    html += '</div>';
                }
                main.innerHTML = html;
            } else if (data.type === 'file') {
                main.innerHTML = `<h3>File: ${data.path}</h3><pre class='explorer-file'>${escapeHtml(data.content)}</pre><button id='back-btn'>Back</button>`;
                document.getElementById('back-btn').onclick = () => {
                    const parent = data.path
                        .replace(/\\|\//g, '/')
                        .replace(/\/[^\/]+$/, '')
                        .replace(/\//g, '/');
                    renderExplorer(parent || '.');
                };
            }
            // Attach click handlers
            document.querySelectorAll('.explorer-link').forEach(link => {
                link.onclick = function(e) {
                    e.preventDefault();
                    const p = this.getAttribute('data-path');
                    renderExplorer(p);
                };
            });
        });
}

function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return text.replace(/[&<>"]'/g, m => map[m]);
}

// On explorer.html, auto-load explorer and set up toolbar
document.addEventListener('DOMContentLoaded', function() {
    let initialPath = '.';
    if (window.location.pathname.startsWith('/explorer')) {
        initialPath = decodeURIComponent(window.location.pathname.replace('/explorer/', '')) || '.';
    } else if (window.location.pathname.startsWith('/explore')) {
        const params = new URLSearchParams(window.location.search);
        initialPath = params.get('path') || '.';
    }
    if (window.location.pathname.startsWith('/explorer') || window.location.pathname.startsWith('/explore')) {
        renderExplorer(initialPath);
        setExplorerView(explorerView);
        document.getElementById('view-list').onclick = function() {
            setExplorerView('list');
            renderExplorer(initialPath);
        };
        document.getElementById('view-icons').onclick = function() {
            setExplorerView('icons');
            renderExplorer(initialPath);
        };
    }
});
