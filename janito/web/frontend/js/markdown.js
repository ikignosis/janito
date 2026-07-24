// Markdown rendering wrapper (marked.js + highlight.js).
//
// Renders model output to HTML with syntax-highlighted code blocks.
// Falls back to plain text if the libraries fail to load.

window.JanitoMarkdown = (function () {
    // Configure marked if available
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true,
            gfm: true,
            highlight: null,   // we highlight manually for control
        });
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function render(text) {
        if (!text) return '';

        if (typeof marked === 'undefined') {
            // Fallback: escape and preserve line breaks
            return '<pre style="white-space:pre-wrap">' + escapeHtml(text) + '</pre>';
        }

        try {
            let html = marked.parse(text);

            // Apply highlight.js to code blocks
            if (typeof hljs !== 'undefined') {
                const template = document.createElement('template');
                template.innerHTML = html;
                template.content.querySelectorAll('pre code').forEach((block) => {
                    try { hljs.highlightElement(block); } catch (e) { /* ignore */ }
                });
                html = template.innerHTML;
            }

            // Sanitize to prevent XSS from model-generated HTML
            if (typeof DOMPurify !== 'undefined') {
                html = DOMPurify.sanitize(html);
            }
            return html;
        } catch (e) {
            console.error('Markdown render error:', e);
            return '<pre style="white-space:pre-wrap">' + escapeHtml(text) + '</pre>';
        }
    }

    return { render, escapeHtml };
})();
