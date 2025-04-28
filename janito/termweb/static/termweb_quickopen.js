// Quick Open (Ctrl+P) modal logic for TermWeb
(function() {
    let allFiles = [];
    let modal = document.getElementById('quickopen-modal');
    let input = document.getElementById('quickopen-input');
    let results = document.getElementById('quickopen-results');
    let selectedIdx = -1;
    let loaded = false;

    // Recursively fetch all file paths from /api/explorer/
    async function fetchAllFiles(path = '.') {
        let files = [];
        try {
            let resp = await fetch(`/api/explorer/${encodeURIComponent(path)}`);
            let data = await resp.json();
            if (data.type === 'dir' && data.entries) {
                for (const entry of data.entries) {
                    const entryPath = path === '.' ? entry.name : path + '/' + entry.name;
                    if (entry.is_dir) {
                        files = files.concat(await fetchAllFiles(entryPath));
                    } else {
                        files.push(entryPath);
                    }
                }
            }
        } catch (e) { console.error('QuickOpen fetch error', e); }
        return files;
    }

    async function ensureLoaded() {
        if (!loaded) {
            allFiles = await fetchAllFiles('.');
            loaded = true;
        }
    }

    function showModal() {
        modal.style.display = 'flex';
        input.value = '';
        results.innerHTML = '';
        selectedIdx = -1;
        setTimeout(() => input.focus(), 50);
    }
    function hideModal() {
        modal.style.display = 'none';
    }

    function renderResults(filtered) {
        results.innerHTML = '';
        filtered.slice(0, 15).forEach((file, idx) => {
            let li = document.createElement('li');
            li.textContent = file;
            li.tabIndex = -1;
            li.className = 'quickopen-result' + (idx === selectedIdx ? ' selected' : '');
            li.onclick = () => openFile(file);
            results.appendChild(li);
        });
    }

    // Improved openFile: poll for file link and click when ready
    function openFile(path) {
        hideModal();
        window.renderExplorer && window.renderExplorer(getParentPath(path), false);
        const maxAttempts = 20; // 20 x 100ms = 2s max
        let attempts = 0;
        function tryClickFile() {
            let fileLinks = document.querySelectorAll(`a.file-link[data-path='${path}']`);
            if (fileLinks.length) {
                fileLinks[0].click();
                // Optionally, add a highlight class
                fileLinks[0].classList.add('quickopen-selected');
            } else if (attempts < maxAttempts) {
                attempts++;
                setTimeout(tryClickFile, 100);
            }
        }
        tryClickFile();
    }

    input.addEventListener('input', async function() {
        await ensureLoaded();
        let q = input.value.trim().toLowerCase();
        let filtered = allFiles.filter(f => f.toLowerCase().includes(q));
        selectedIdx = -1;
        renderResults(filtered);
    });
    input.addEventListener('keydown', function(e) {
        let items = results.querySelectorAll('li');
        if (e.key === 'ArrowDown') {
            selectedIdx = Math.min(selectedIdx + 1, items.length - 1);
            renderResults(Array.from(items).map(li => li.textContent));
            e.preventDefault();
        } else if (e.key === 'ArrowUp') {
            selectedIdx = Math.max(selectedIdx - 1, 0);
            renderResults(Array.from(items).map(li => li.textContent));
            e.preventDefault();
        } else if (e.key === 'Enter') {
            if (selectedIdx >= 0 && items[selectedIdx]) {
                openFile(items[selectedIdx].textContent);
            } else if (items.length === 1) {
                openFile(items[0].textContent);
            }
        } else if (e.key === 'Escape') {
            hideModal();
        }
    });

    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'p' && !e.shiftKey && !e.altKey) {
            showModal();
            e.preventDefault();
        } else if (e.key === 'Escape' && modal.style.display === 'flex') {
            hideModal();
        }
    });
    modal.addEventListener('mousedown', function(e) {
        if (e.target === modal) hideModal();
    });

    // Helper: get parent path
    function getParentPath(path) {
        path = (path || '').replace(/\\/g, '/').replace(/^\/+/g, '').replace(/\/+$/g, '');
        if (!path || path === '.' || path === '') return '.';
        const parts = path.split('/');
        if (parts.length <= 1) return '.';
        parts.pop();
        const parent = parts.join('/');
        return parent === '' ? '.' : parent;
    }

    // Style for selected result and quickopen-selected file link
    let style = document.createElement('style');
    style.textContent = `.quickopen-result.selected { background:#333; color:#8be9fd; } .quickopen-result { padding:0.3em 0.7em; cursor:pointer; border-radius:0.3em; } .quickopen-result:hover { background:#222; } a.file-link.quickopen-selected { background:#444 !important; color:#8be9fd !important; border-radius:0.3em; }`;
    document.head.appendChild(style);
})();
