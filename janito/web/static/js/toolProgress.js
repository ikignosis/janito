import { formatToolProgress } from "../js/progressFormatter.js";

export function handleToolProgress(progress, terminal) {
  console.debug("[WebClient] Tool progress event:", progress);

  const callId = progress.call_id || 'unknown';
  let container = document.getElementById(`call-${callId}`);
  if (!container) {
    container = document.createElement("div");
    container.id = `call-${callId}`;
    container.className = "breadcrumb-container";
    terminal.appendChild(container);
  }

  let msg = '';
  if (progress.event === 'start') {
    msg = `<b>[${progress.tool}]</b> <span style='color:blue'>Started</span> with args: <code>${JSON.stringify(progress.args)}</code>`;
  } else if (progress.event === 'finish') {
    if (progress.error) {
      msg = `<b>[${progress.tool}]</b> <span style='color:red'>Error</span>: <code>${progress.error}</code>`;
    } else {
      msg = `<b>[${progress.tool}]</b> <span style='color:green'>Finished</span> result: <code>${typeof progress.result === 'object' ? JSON.stringify(progress.result) : progress.result}</code>`;
    }
  } else if (progress.event === 'progress') {
    msg = `<b>[${progress.tool || ''}]</b> ${progress.message}`;
  } else {
    msg = formatToolProgress(progress);
  }

  container.innerHTML += `<div class='breadcrumb-tab'>${msg}</div>`;
}

