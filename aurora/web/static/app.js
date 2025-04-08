document.addEventListener('DOMContentLoaded', function() {

// Create modal if it doesn't exist
if (!document.getElementById('content-modal')) {
  const modal = document.createElement('div');
  modal.id = 'content-modal';
  modal.style.display = 'none';
  modal.style.position = 'fixed';
  modal.style.top = '0';
  modal.style.left = '0';
  modal.style.width = '100%';
  modal.style.height = '100%';
  modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
  modal.style.zIndex = '1000';
  modal.innerHTML = `
    <div style=\"background:#fff; margin:5% auto; padding:20px; max-width:80%; max-height:80%; overflow:auto;\">
      <button onclick=\"document.getElementById('content-modal').style.display='none'\">Close</button>
      <pre id=\"modal-content\" style=\"white-space: pre-wrap;\"></pre>
    </div>`;
  document.body.appendChild(modal);
}

window.showPopup = function(content) {
  document.getElementById('modal-content').textContent = content;
  document.getElementById('content-modal').style.display = 'block';
}


const terminal = document.getElementById('terminal');
const inputLine = document.getElementById('input-line');
const output = document.getElementById('output');

// Initialize input line with prompt and blinking cursor
document.getElementById('input-container').innerHTML = '&nbsp;<span class="cursor"></span>';

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
  const inputLine = document.getElementById('input-line');
  terminal.appendChild(line);
  if (shouldScroll) {
    scrollToBottom(terminal);
  }
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
  const inputLine = document.getElementById('input-line');
  terminal.appendChild(container);
  if (shouldScroll) {
    scrollToBottom(terminal);
  }
}

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
  document.getElementById('input-container').innerHTML = (command || '&nbsp;') + '<span class="cursor"></span>';


});

// Create modal if it doesn't exist
if (!document.getElementById('content-modal')) {
  const modal = document.createElement('div');
  modal.id = 'content-modal';
  modal.style.display = 'none';
  modal.style.position = 'fixed';
  modal.style.top = '0';
  modal.style.left = '0';
  modal.style.width = '100%';
  modal.style.height = '100%';
  modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
  modal.style.zIndex = '1000';
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


async function sendCommandStream(cmd) {
  const response = await fetch('/execute_stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ input: cmd })
  

});

// Create modal if it doesn't exist
if (!document.getElementById('content-modal')) {
  const modal = document.createElement('div');
  modal.id = 'content-modal';
  modal.style.display = 'none';
  modal.style.position = 'fixed';
  modal.style.top = '0';
  modal.style.left = '0';
  modal.style.width = '100%';
  modal.style.height = '100%';
  modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
  modal.style.zIndex = '1000';
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


  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while(true) {
    const { done, value } = await reader.read();
    if(done) break;
    buffer += decoder.decode(value, {stream:true

});

// Create modal if it doesn't exist
if (!document.getElementById('content-modal')) {
  const modal = document.createElement('div');
  modal.id = 'content-modal';
  modal.style.display = 'none';
  modal.style.position = 'fixed';
  modal.style.top = '0';
  modal.style.left = '0';
  modal.style.width = '100%';
  modal.style.height = '100%';
  modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
  modal.style.zIndex = '1000';
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
            const progress = data.data;
            console.debug('[WebClient] Tool progress event:', progress);
            let msg = '';
            if(progress.event !== 'start' && progress.event !== 'finish') {
              msg = `🔧 <b>[Tool ${progress.tool}]</b> <b>${progress.event.toUpperCase()}</b>`;
            }
            if(progress.event === 'start') {
              if(progress.args && typeof progress.args === 'object') {
                let breadcrumb = '';
                switch(progress.tool) {
                  case 'view_file':
                    breadcrumb = `Viewing &gt; ${progress.args.path}`;
                    const start = progress.args.start_line;
                    const end = progress.args.end_line;
                    if (start !== undefined || end !== undefined) {
                      breadcrumb += ' &gt; ';
                      breadcrumb += (start !== undefined ? start : '') + '-' + (end !== undefined ? end : '');
                    }
                    break;
                  case 'create_file':
                    breadcrumb = `Creating file &gt; ${progress.args.path}`;
                    break;
                  case 'create_directory':
                    breadcrumb = `Creating directory &gt; ${progress.args.path}`;
                    break;
                  case 'move_file':
                    breadcrumb = `Moving &gt; ${progress.args.source_path} &rarr; ${progress.args.destination_path}`;
                    break;
                  case 'remove_file':
                    breadcrumb = `Removing &gt; ${progress.args.path}`;
                    break;
                  case 'file_str_replace':
                    breadcrumb = `Replacing in &gt; ${progress.args.path}`;
                    break;
                  case 'find_files':
                    breadcrumb = `Searching in &gt; ${progress.args.directory}`;
                    break;
                  case 'search_text':
                    breadcrumb = `Searching text in &gt; ${progress.args.directory}`;
                    break;
                  case 'bash_exec':
                    breadcrumb = `Running command`;
                    break;
                  case 'fetch_url':
                    breadcrumb = `Fetching URL &gt; ${progress.args.url}`;
                    break;
                  case 'ask_user':
                    breadcrumb = `User input`;
                    break;
                  default:
                    const argSummary = Object.entries(progress.args)
                      .map(([k, v]) => `${k}: ${v}`)
                      .join(', ');
                    breadcrumb = `[${progress.tool}] &gt; ${argSummary}`;
                }
                msg += `<div class=\"breadcrumb-tab\">${breadcrumb}</div>`;
              }
            } else if(progress.event === 'finish') {
              if(progress.error) {
                msg += `<br>Error: <code>${progress.error}</code>`;
              } else if(progress.args && typeof progress.args === 'object') {
                let breadcrumb = '';
                switch(progress.tool) {
                  case 'view_file':
                    let lineCount = 0;
                    if (progress.result && typeof progress.result === 'string') {
                      lineCount = progress.result.split(/\r?\n/).length;
                    }
                    const safeContent = content.replace(/</g, "&lt;").replace(/>/g, "&gt;");
const link = `<a href="#" onclick="showPopup(\`${safeContent.replace(/`/g, '\\`')}\`); return false;">Show content</a>`;
breadcrumb = `Viewed ${lineCount} line${lineCount !== 1 ? 's' : ''} (${link})`;
                    break;
                  case 'create_file':
                    breadcrumb = `Finished creating file &gt; ${progress.args.path}`;
                    break;
                  case 'create_directory':
                    breadcrumb = `Finished creating directory &gt; ${progress.args.path}`;
                    break;
                  case 'move_file':
                    breadcrumb = `Finished moving &gt; ${progress.args.source_path} &rarr; ${progress.args.destination_path}`;
                    break;
                  case 'remove_file':
                    breadcrumb = `Finished removing &gt; ${progress.args.path}`;
                    break;
                  case 'file_str_replace':
                    breadcrumb = `Finished replacing in &gt; ${progress.args.path}`;
                    break;
                  case 'find_files':
                    breadcrumb = `Finished searching in &gt; ${progress.args.directory}`;
                    break;
                  case 'search_text':
                    breadcrumb = `Finished searching text in &gt; ${progress.args.directory}`;
                    break;
                  case 'bash_exec':
                    breadcrumb = `Finished running command`;
                    break;
                  case 'fetch_url':
                    breadcrumb = `Finished fetching URL &gt; ${progress.args.url}`;
                    break;
                  case 'ask_user':
                    breadcrumb = `User input finished`;
                    break;
                  default:
                    const argSummary = Object.entries(progress.args)
                      .map(([k, v]) => `${k}: ${v}`)
                      .join(', ');
                    breadcrumb = `[${progress.tool}] finished &gt; ${argSummary}`;
                }
                msg += `<div class=\"breadcrumb-tab\">${breadcrumb}</div>`;
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
              const inputLine = document.getElementById('input-line');
              document.getElementById('terminal').appendChild(container);
            }
            container.innerHTML += msg;
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



});

// Create modal if it doesn't exist
if (!document.getElementById('content-modal')) {
  const modal = document.createElement('div');
  modal.id = 'content-modal';
  modal.style.display = 'none';
  modal.style.position = 'fixed';
  modal.style.top = '0';
  modal.style.left = '0';
  modal.style.width = '100%';
  modal.style.height = '100%';
  modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
  modal.style.zIndex = '1000';
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

