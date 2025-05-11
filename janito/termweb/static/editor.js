// --- Load file content via AJAX if ?path=... is present ---
function getQueryParam(name) {
    const url = new URL(window.location.href);
    return url.searchParams.get(name);
}
const filePath = getQueryParam('path');

// Updates the theme icon based on the current theme
function updateThemeIcon() {
    var icon = document.getElementById('theme-icon');
    if (!icon) return;
    if (document.body.classList.contains('light-theme')) {
        icon.textContent = '☀️'; // Sun for light mode
        icon.title = 'Switch to dark mode';
    } else {
        icon.textContent = '🌙'; // Moon for dark mode
        icon.title = 'Switch to light mode';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Display filename in header if present
    if (filePath) {
        const filename = filePath.split(/[\\\/]/).pop();
        const filenameDisplay = document.getElementById('filename-display');
        if (filenameDisplay) {
            filenameDisplay.textContent = '— ' + filePath;
            filenameDisplay.title = filePath;
        }
    }

    let initialContent = "";
    if (filePath) {
        fetch(`/api/explorer/${encodeURIComponent(filePath)}`)
            .then(resp => resp.json())
            .then(data => {
                if (data.type === 'file') {
                    initialContent = data.content;
                    if (window.editorInstance) {
                        window.editorInstance.setValue(initialContent);
                    }
                } else if (data.error) {
                    initialContent = '# Error: ' + data.error;
                    if (window.editorInstance) {
                        window.editorInstance.setValue(initialContent);
                    }
                }
            })
            .catch(err => {
                initialContent = '# Error ao carregar arquivo: ' + err;
                if (window.editorInstance) {
                    window.editorInstance.setValue(initialContent);
                }
            });
    }

    // --- Detect file extension and set CodeMirror mode ---
    function detectMode(filename) {
        if (!filename) return 'python';
        const ext = filename.split('.').pop().toLowerCase();
        const map = {
            'py': 'python',
            'js': 'javascript',
            'json': 'javascript',
            'md': 'markdown',
            'html': {name: 'htmlmixed', scriptingModeSpec: 'django'},
            'htm': {name: 'htmlmixed', scriptingModeSpec: 'django'},
            'jinja': 'django',
            'j2': 'django',
            'jinja2': 'django',
            'css': 'css',
            'sh': 'shell',
            'bash': 'shell',
            'yml': 'yaml',
            'yaml': 'yaml',
        };
        return map[ext] || 'python';
    }
    var initialMode = detectMode(filePath);
    var editorInstance = CodeMirror.fromTextArea(document.getElementById('code'), {
        lineNumbers: true,
        mode: initialMode,
        theme: 'dracula',
        indentUnit: 4,
        tabSize: 4,
        styleActiveLine: true,
    });
    // If file loaded later, update mode
    if (filePath) {
        const mode = detectMode(filePath);
        editorInstance.setOption('mode', mode);
    }
    window.editorInstance = editorInstance;


    // Add Ctrl-F handler for find
    editorInstance.addKeyMap({
        'Ctrl-F': function(cm) {
            cm.execCommand('find');
        },
        'Cmd-F': function(cm) {
            cm.execCommand('find');
        },
        'Ctrl-S': function(cm) {
            document.getElementById('save-btn').click();
            // Prevent default browser save dialog
            return false;
        },
        'Cmd-S': function(cm) {
            document.getElementById('save-btn').click();
            return false;
        },
        'Alt-W': function(cm) {
            const current = cm.getOption('lineWrapping');
            cm.setOption('lineWrapping', !current);
        }
    });
    // --- Custom floating find navigation panel ---
    function createFindPanel() {
        let panel = document.getElementById('find-nav-panel');
        if (!panel) {
            panel = document.createElement('div');
            panel.id = 'find-nav-panel';
            panel.style.position = 'absolute';
            panel.style.top = '70px';
            panel.style.right = '30px';
            panel.style.zIndex = 200;
            panel.style.background = 'rgba(40,42,54,0.98)';
            panel.style.color = '#fff';
            panel.style.borderRadius = '6px';
            panel.style.boxShadow = '0 2px 8px #0008';
            panel.style.padding = '4px 10px 4px 8px';
            panel.style.display = 'flex';
            panel.style.alignItems = 'center';
            panel.style.gap = '8px';
            panel.style.fontSize = '1em';
            panel.style.userSelect = 'none';
            panel.innerHTML = `
                <button id="find-prev-btn" title="Previous match" style="background:none;border:none;color:#fff;font-size:1.2em;cursor:pointer;">⏮️</button>
                <span id="find-match-info">1/1</span>
                <button id="find-next-btn" title="Next match" style="background:none;border:none;color:#fff;font-size:1.2em;cursor:pointer;">⏭️</button>
            `;
            document.body.appendChild(panel);
        }
        return panel;
    }
    function removeFindPanel() {
        let panel = document.getElementById('find-nav-panel');
        if (panel) panel.remove();
    }
    // Hook into CodeMirror search dialog
    let lastSearchState = null;
    function updateFindPanel(cm) {
        let state = cm.state.search;
        if (!state || !state.query) {
            removeFindPanel();
            return;
        }
        let matches = 0, current = 0;
        if (state.overlay && state.overlay.matches) {
            matches = state.overlay.matches.length;
            current = state.overlay.matches.findIndex(m => m.from && cm.getCursor().line === m.from.line && cm.getCursor().ch >= m.from.ch && cm.getCursor().ch <= m.to.ch) + 1;
        }
        // fallback: count marked text
        if (!matches) {
            let marks = cm.getAllMarks();
            let found = marks.filter(m => m.className && m.className.includes('cm-searching'));
            matches = found.length;
            let cur = cm.getCursor();
            current = found.findIndex(m => {
                let pos = m.find();
                return pos && pos.from.line === cur.line && cur.ch >= pos.from.ch && cur.ch <= pos.to.ch;
            }) + 1;
        }
        if (!matches) matches = 1;
        if (!current) current = 1;
        createFindPanel();
        document.getElementById('find-match-info').textContent = `${current}/${matches}`;
    }
    editorInstance.on('cursorActivity', function(cm) {
        updateFindPanel(cm);
    });
    editorInstance.on('search', function(cm) {
        updateFindPanel(cm);
    });
    // Listen for dialog open/close
    let observer = new MutationObserver(function() {
        let dialogs = document.querySelectorAll('.CodeMirror-dialog');
        if (dialogs.length) {
            setTimeout(() => updateFindPanel(editorInstance), 100);
        } else {
            removeFindPanel();
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    // Button handlers
    document.body.addEventListener('click', function(e) {
        if (e.target && e.target.id === 'find-next-btn') {
            editorInstance.execCommand('findNext');
        } else if (e.target && e.target.id === 'find-prev-btn') {
            editorInstance.execCommand('findPrev');
        }
    });
    // --- END custom find panel ---
    // Dynamically calculate available height
    function resizeEditor() {
        var header = document.querySelector('.header');
        var headerHeight = header ? header.offsetHeight : 0;
        var availableHeight = window.innerHeight - headerHeight;
        editorInstance.setSize('100%', availableHeight + 'px');
    }
    window.addEventListener('resize', resizeEditor);
    setTimeout(resizeEditor, 0);
    editorInstance.setValue(initialContent);
    updateThemeIcon();

    // Set initial state
    document.body.classList.remove('light-theme');
    editorInstance.setOption('theme', 'dracula');
    updateThemeIcon();

    // Theme switch button logic
    var themeSwitcher = document.getElementById('theme-switcher');
    if (themeSwitcher) {
        themeSwitcher.addEventListener('click', function() {
            var isLight = document.body.classList.toggle('light-theme');
            if (isLight) {
                editorInstance.setOption('theme', 'default');
            } else {
                editorInstance.setOption('theme', 'dracula');
            }
            updateThemeIcon();
        });
    }
    // Botão de Gravar
    var saveBtn = document.getElementById('save-btn');
    saveBtn.addEventListener('click', function() {
        if (!filePath) {
            alert('Nenhum arquivo aberto para gravar.');
            return;
        }
        const content = editorInstance.getValue();
        fetch(`/api/explorer/${encodeURIComponent(filePath)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ content }),
        })
        .then(resp => resp.json())
        .then(data => {
            if (data.success) {
                // Show popup
                var popup = document.getElementById('save-popup');
                popup.style.display = 'block';
                setTimeout(() => { popup.style.display = 'none'; }, 1500);
            } else {
                alert('Error saving: ' + (data.error || 'desconhecido'));
            }
        })
        .catch(err => {
            alert('Error saving: ' + err);
        });
    });
});
