document.addEventListener('DOMContentLoaded', function() {

  // --- Modal Setup ---
  function createContentModal() {
    if (document.getElementById('content-modal')) return;
    const modal = document.createElement('div');
    modal.id = 'content-modal';
    Object.assign(modal.style, {
      display: 'none',
      position: 'fixed',
      top: '0',
      left: '0',
      width: '100%',
      height: '100%',
      backgroundColor: 'rgba(0,0,0,0.5)',
      zIndex: '1000'
    });
    modal.innerHTML = `
      <div style="background:#fff; margin:5% auto; padding:20px; max-width:80%; max-height:80%; overflow:auto;">
        <button onclick="document.getElementById('content-modal').style.display='none'">Close</button>
        <pre id="modal-content" style="white-space: pre-wrap;"></pre>
      </div>`;
    document.body.appendChild(modal);
  }

  window.showPopup = function(content) {
    document.getElementById('modal-content').textContent = content;
    document.getElementById('content-modal').style.display = 'block';
  }

  createContentModal();

  // --- Terminal Helpers ---
  const terminal = document.getElementById('terminal');
  let command = '';

  function isScrolledToBottom(element) {
    return element.scrollHeight - element.clientHeight <= element.scrollTop + 5;
  }

  function scrollToBottom(element) {
    element.scrollTop = element.scrollHeight;
  }

  function appendToTerminal(text) {
    const shouldScroll = isScrolledToBottom(terminal);
    const line = document.createElement('div');
    line.innerHTML = text;
    terminal.appendChild(line);
    if (shouldScroll) scrollToBottom(terminal);
  }

  function appendOutput(content, cssClass = '') {
    const shouldScroll = isScrolledToBottom(terminal);
    let html = '';
    if (typeof content === 'string') {
      html = marked.parse(content);
    } else {
      html = '<pre>' + JSON.stringify(content, null, 2) + '</pre>';
    }
    const container = document.createElement('div');
    container.className = 'markdown-content ' + cssClass;
    container.innerHTML = html;
    terminal.appendChild(container);
    if (shouldScroll) scrollToBottom(terminal);
  }

  // --- Command Input Handling ---
  const inputContainer = document.getElementById('input-container');
  function updateInputDisplay() {
    inputContainer.innerHTML = (command || '&nbsp;') + '<span class="cursor"></span>';
  }
  updateInputDisplay();

  document.addEventListener('keydown', function(event) {
    if (event.key === 'Backspace') {
      command = command.slice(0, -1);
    } else if (event.key === 'Enter') {
      appendToTerminal('<span class="user-input">' + command + '</span>');
      sendCommandStream(command);
      command = '';
    } else if (event.key.length === 1) {
      command += event.key;
    }
    updateInputDisplay();
  });

  // --- Streaming Command Execution ---
  async function sendCommandStream(cmd) {
    const response = await fetch('/execute_stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input: cmd })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while(true) {
      const { done, value } = await reader.read();
      if(done) break;
      buffer += decoder.decode(value, {stream:true});

      let parts = buffer.split('\n\n');
      buffer = parts.pop();

      for(const part of parts) {
        if(part.startsWith('data: ')) {
          const jsonStr = part.slice(6).trim();
          try {
            const data = JSON.parse(jsonStr);

            if(data.type === 'content' && data.content) {
              appendOutput(data.content);
            } else if(data.type === 'tool_progress') {
              handleToolProgress(data.data);
            } else if(data.type === 'error') {
              appendOutput('Error: ' + data.error);
            }
          } catch(e) {
            console.error('Error parsing SSE data', e, jsonStr);
          }
        }
      }
    }
  }

  function handleToolProgress(progress) {
    console.debug('[WebClient] Tool progress event:', progress);
    let msg = '';
    if(progress.event !== 'start' && progress.event !== 'finish') {
      msg = `🔧 <b>[Tool ${progress.tool}]</b> <b>${progress.event.toUpperCase()}</b>`;
    }
    if(progress.event === 'start') {
      msg += `<div class="breadcrumb-tab">${formatBreadcrumb(progress, true)}</div>`;
    } else if(progress.event === 'finish') {
      if(progress.error) {
        msg += `<br>Error: <code>${progress.error}</code>`;
      } else {
        msg += `<div class="breadcrumb-tab">${formatBreadcrumb(progress, false)}</div>`;
      }
    } else {
      msg += `<br>Data: <code>${JSON.stringify(progress, null, 2)}</code>`;
    }

    const callId = progress.call_id;
    let container = document.getElementById(`call-${callId}`);
    if (!container) {
      container = document.createElement('div');
      container.id = `call-${callId}`;
      container.className = 'breadcrumb-container';
      terminal.appendChild(container);
    }
    container.innerHTML += msg;
  }

  function formatBreadcrumb(progress, isStart) {
    const args = progress.args || {};
    let breadcrumb = '';
    if(isStart) {
      switch(progress.tool) {
        case 'view_file':
          breadcrumb = `Viewing &gt; ${args.path}`;
          const start = args.start_line;
          const end = args.end_line;
          if (start !== undefined || end !== undefined) {
            breadcrumb += ' &gt; ';
            breadcrumb += (start !== undefined ? start : '') + '-' + (end !== undefined ? end : '');
          }
          break;
        case 'create_file':
          breadcrumb = `Creating file &gt; ${args.path}`; break;
        case 'create_directory':
          breadcrumb = `Creating directory &gt; ${args.path}`; break;
        case 'move_file':
          breadcrumb = `Moving &gt; ${args.source_path} &rarr; ${args.destination_path}`; break;
        case 'remove_file':
          breadcrumb = `Removing &gt; ${args.path}`; break;
        case 'file_str_replace':
          breadcrumb = `Replacing in &gt; ${args.path}`; break;
        case 'find_files':
          breadcrumb = `Searching in &gt; ${args.directory}`; break;
        case 'search_text':
          breadcrumb = `Searching text in &gt; ${args.directory}`; break;
        case 'bash_exec':
          breadcrumb = `Running command`; break;
        case 'fetch_url':
          breadcrumb = `Fetching URL &gt; ${args.url}`; break;
        case 'ask_user':
          breadcrumb = `User input`; break;
        default:
          breadcrumb = `[${progress.tool}] &gt; ` + Object.entries(args).map(([k,v])=>`${k}: ${v}`).join(', ');
      }
    } else {
      switch(progress.tool) {
        case 'view_file':
          let lineCount = 0;
          let content = '';
          if (progress.result && typeof progress.result === 'string') {
            content = progress.result;
            lineCount = content.split(/\r?\n/).length;
          }
          const safeContent = content.replace(/</g, "&lt;").replace(/>/g, "&gt;");
          const link = `<a href="#" onclick="showPopup(\`${safeContent.replace(/`/g, '\\`')}\`); return false;">Show content</a>`;
          breadcrumb = `Viewed ${lineCount} line${lineCount !== 1 ? 's' : ''} (${link})`;
          break;
        case 'create_file':
          breadcrumb = `Finished creating file &gt; ${args.path}`; break;
        case 'create_directory':
          breadcrumb = `Finished creating directory &gt; ${args.path}`; break;
        case 'move_file':
          breadcrumb = `Finished moving &gt; ${args.source_path} &rarr; ${args.destination_path}`; break;
        case 'remove_file':
          breadcrumb = `Finished removing &gt; ${args.path}`; break;
        case 'file_str_replace':
          breadcrumb = `Finished replacing in &gt; ${args.path}`; break;
        case 'find_files':
          breadcrumb = `Finished searching in &gt; ${args.directory}`; break;
        case 'search_text':
          breadcrumb = `Finished searching text in &gt; ${args.directory}`; break;
        case 'bash_exec':
          breadcrumb = `Finished running command`; break;
        case 'fetch_url':
          breadcrumb = `Finished fetching URL &gt; ${args.url}`; break;
        case 'ask_user':
          breadcrumb = `User input finished`; break;
        default:
          breadcrumb = `[${progress.tool}] finished &gt; ` + Object.entries(args).map(([k,v])=>`${k}: ${v}`).join(', ');
      }
    }
    return breadcrumb;
  }

});
