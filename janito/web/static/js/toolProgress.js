import { formatToolProgress } from "../js/progressFormatter.js";

export function handleToolProgress(progress) {
  console.log('[DEBUG] handleToolProgress called with:', progress);
  console.debug("[WebClient] Tool progress event:", progress);

  const sidebar = document.getElementById('tool-activity-content');
  if (!sidebar) return;

  const callId = progress.call_id || 'unknown';
  let container = sidebar.querySelector(`#call-${callId}`);
  if (!container) {
    container = document.createElement("div");
    container.id = `call-${callId}`;
    container.className = "tool-activity-block";
    sidebar.appendChild(container);
  }

  let msg = '';
  // Tool running state management
  const terminal = document.getElementById('terminal');
  const progressBar = document.getElementById('tool-progress-bar');
  if (!window.activeToolCalls) window.activeToolCalls = new Set();

  if (progress.event === 'start') {
    if (progress.call_id) window.activeToolCalls.add(progress.call_id);
    if (progressBar) {
      progressBar.style.display = '';
      progressBar.classList.add('flashing');
    }
    if (terminal) terminal.classList.add('tool-running');
    return;
  }
  if (progress.event === 'finish') {
    if (progress.call_id) window.activeToolCalls.delete(progress.call_id);
    if (window.activeToolCalls.size === 0) {
      if (progressBar) progressBar.style.display = 'none';
      if (terminal) terminal.classList.remove('tool-running');
    }
    return;
  }
  if (
    progress.type === 'tool_call' ||
    progress.type === 'tool_result'
  ) {
    return;
  }

  function humanizeToolName(tool) {
    if (!tool) return '';
    return tool.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/Tool$/, '').replace(/^./, s => s.toUpperCase());
  }
  const toolLabel = humanizeToolName(progress.tool);

  // Group info + success/error on the same line
  if (!container.lastInfoEntry) {
    container.lastInfoEntry = null;
  }

  if (progress.type === 'info') {
    // Start a new line for info
    const entry = document.createElement('div');
    entry.className = 'tool-activity-entry';
    entry.innerHTML = `<span style='color:#0078d4'>${progress.message}</span>`;
    container.appendChild(entry);
    container.lastInfoEntry = entry;
    // Flash the progress bar if tool is running
    if (progressBar && window.activeToolCalls && window.activeToolCalls.size > 0) {
      progressBar.classList.add('flash-once');
      setTimeout(() => progressBar.classList.remove('flash-once'), 400);
    }
  } else if (progress.type === 'success') {
    // Append to last info entry if exists, else new line
    if (container.lastInfoEntry) {
      container.lastInfoEntry.innerHTML += ` <span style='color:green'>${progress.message}</span>`;
      container.lastInfoEntry = null;
    } else {
      const entry = document.createElement('div');
      entry.className = 'tool-activity-entry';
      entry.innerHTML = `<span style='color:green'>${progress.message}</span>`;
      container.appendChild(entry);
    }
  } else if (progress.type === 'error') {
    if (container.lastInfoEntry) {
      container.lastInfoEntry.innerHTML += ` <span style='color:red'>${progress.message}</span>`;
      container.lastInfoEntry = null;
    } else {
      const entry = document.createElement('div');
      entry.className = 'tool-activity-entry';
      entry.innerHTML = `<span style='color:red'>${progress.message}</span>`;
      container.appendChild(entry);
    }
  } else if (progress.type === 'stdout') {
    const entry = document.createElement('div');
    entry.className = 'tool-activity-entry';
    entry.innerHTML = `<span style='color:#aaa'>${progress.message}</span>`;
    container.appendChild(entry);
  } else if (progress.type === 'stderr') {
    const entry = document.createElement('div');
    entry.className = 'tool-activity-entry';
    entry.innerHTML = `<span style='color:orange'>${progress.message}</span>`;
    container.appendChild(entry);
  } else if (progress.event === 'progress') {
    const entry = document.createElement('div');
    entry.className = 'tool-activity-entry';
    entry.innerHTML = `${progress.message}`;
    container.appendChild(entry);
  } else {
    const entry = document.createElement('div');
    entry.className = 'tool-activity-entry';
    entry.innerHTML = formatToolProgress(progress);
    container.appendChild(entry);
  }
  sidebar.scrollTop = sidebar.scrollHeight;
}


