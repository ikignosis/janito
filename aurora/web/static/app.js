document.addEventListener('DOMContentLoaded', function() {

const terminal = document.getElementById('terminal');
const inputLine = document.getElementById('input-line');
const output = document.getElementById('output');

// Initialize input line with prompt and blinking cursor
document.getElementById('input-container').innerHTML = '<span class="cursor"></span>';

let command = '';

function appendToTerminal(text) {
  const line = document.createElement('div');
  line.innerHTML = text;
  terminal.insertBefore(line, output);
}

function appendOutput(content, cssClass = '') {
  let html = '';
  if (typeof content === 'string') {
    html = marked.parse(content);
  } else {
    html = '<pre>' + JSON.stringify(content, null, 2) + '</pre>';
  }
  const container = document.createElement('div');
  container.className = 'markdown-content ' + cssClass;
  container.innerHTML = html;
  terminal.insertBefore(container, output);
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
  document.getElementById('input-container').innerHTML = command + '<span class="cursor"></span>';
});

async function sendCommandStream(cmd) {
  const response = await fetch('/execute_stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
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
          console.log('[WebClient] SSE event received:', data);
          if(data.type === 'content' && data.content) {
            appendOutput(data.content);
          } else if(data.type === 'tool_progress') {
            const progress = data.data;
            console.debug('[WebClient] Tool progress event:', progress);
            let msg = `🔧 <b>[Tool ${progress.tool}]</b> <b>${progress.event.toUpperCase()}</b>`;
            if(progress.event === 'start') {
              if(progress.tool === 'view_file' && progress.args && progress.args.path) {
                msg += `<div class="breadcrumb-tab">Viewing &gt; ${progress.args.path}</div>`;
              } else {
                msg += `<br>Args: <code>${JSON.stringify(progress.args, null, 2)}</code>`;
              }
            } else if(progress.event === 'finish') {
              if(progress.error) {
                msg += `<br>Error: <code>${progress.error}</code>`;
              } else {
                msg += `<br>Result: <code>${JSON.stringify(progress.result, null, 2)}</code>`;
              }
            } else {
              msg += `<br>Data: <code>${JSON.stringify(progress, null, 2)}</code>`;
            }
            appendOutput(msg, 'tool-progress');
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
