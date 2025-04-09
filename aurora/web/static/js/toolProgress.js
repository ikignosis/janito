import { formatProgress } from "../js/progressFormatter.js";

export function handleToolProgress(progress, terminal) {
  console.debug("[WebClient] Tool progress event:", progress);
  let msg = "";
  if(progress.event !== "start" && progress.event !== "finish") {
    msg = `🔧 <b>[Tool ${progress.tool}]</b> <b>${progress.event.toUpperCase()}</b>`;
  }
  if(progress.event === "start") {
    msg += `<div class="breadcrumb-tab">${formatBreadcrumb(progress, true)}</div>`;
  } else if(progress.event === "finish") {
    if(progress.error) {
      msg += `<br>Error: <code>${progress.error}</code>`;
    } else {
      msg += `<div class="breadcrumb-tab">${formatProgress(progress, progress.args || {})}</div>`;
    }
  } else {
    msg += `<br>Data: <code>${JSON.stringify(progress, null, 2)}</code>`;
  }

  const callId = progress.call_id;
  let container = document.getElementById(`call-${callId}`);
  if (!container) {
    container = document.createElement("div");
    container.id = `call-${callId}`;
    container.className = "breadcrumb-container";
    terminal.appendChild(container);
  }
  container.innerHTML += msg;
}

export function formatBreadcrumb(progress, isStart) {
  const args = progress.args || {};
  let breadcrumb = "";
  if(isStart) {
    switch(progress.tool) {
      case "view_file":
        breadcrumb = `Viewing &gt; ${args.path}`;
        const start = args.start_line;
        const end = args.end_line;
        if (start !== undefined || end !== undefined) {
          breadcrumb += " &gt; ";
          breadcrumb += (start !== undefined ? start : "") + "-" + (end !== undefined ? end : "");
        }
        break;
      case "create_file":
        breadcrumb = `Creating file &gt; ${args.path}`; break;
      case "create_directory":
        breadcrumb = `Creating directory &gt; ${args.path}`; break;
      case "move_file":
        breadcrumb = `Moving &gt; ${args.source_path} &rarr; ${args.destination_path}`; break;
      case "remove_file":
        breadcrumb = `Removing &gt; ${args.path}`; break;
      case "file_str_replace":
        breadcrumb = `Replacing in &gt; ${args.path}`; break;
      case "find_files":
        breadcrumb = `Searching in &gt; ${args.directory}`; break;
      case "search_text":
        breadcrumb = `Searching text in &gt; ${args.directory}`; break;
      case "bash_exec":
        breadcrumb = "Running command"; break;
      case "fetch_url":
        breadcrumb = `Fetching URL &gt; ${args.url}`; break;
      case "ask_user":
        breadcrumb = "User input"; break;
      default:
        breadcrumb = `[${progress.tool}] &gt; ` + Object.entries(args).map(([k,v])=>`${k}: ${v}`).join(", ");
    }
  } else {
    switch(progress.tool) {
      case "view_file":
        let lineCount = 0;
        let content = "";
        if (progress.result && typeof progress.result === "string") {
          content = progress.result;
          lineCount = content.split(/\r?\n/).length;
        }
        const safeContent = content.replace(/</g, "&lt;").replace(/>/g, "&gt;");
        const escapedContent = safeContent.replace(/\\/g, "\\\\").replace(/`/g, "\\`").replace(/\$\{/g, "\\${}");
let lang = "";
if(args.path) {
  if(args.path.endsWith(".py")) lang = "python";
  else if(args.path.endsWith(".sh") || args.path.endsWith(".bash")) lang = "bash";
  else if(args.path.endsWith(".json")) lang = "json";
  else if(args.path.endsWith(".md") || args.path.endsWith(".markdown")) lang = "markdown";
}
const index = window.contentStore.push(content) - 1;
const link = `<a href="#" onclick="showContentPopup(${index}, '${lang}'); return false;">${lineCount} line${lineCount !== 1 ? "s" : ""}</a>`;
        breadcrumb = `Viewing ${link}`;
        break;
      case "create_file":
        breadcrumb = `Finished creating file &gt; ${args.path}`; break;
      case "create_directory":
        breadcrumb = `Finished creating directory &gt; ${args.path}`; break;
      case "move_file":
        breadcrumb = `Finished moving &gt; ${args.source_path} &rarr; ${args.destination_path}`; break;
      case "remove_file":
        breadcrumb = `Finished removing &gt; ${args.path}`; break;
      case "file_str_replace":
        breadcrumb = `Finished replacing in &gt; ${args.path}`; break;
      case "find_files": {
        let count = 0;
        if(Array.isArray(progress.result)) {
          count = progress.result.length;
        } else if(typeof progress.result === 'string') {
          count = progress.result.trim() === '' ? 0 : progress.result.trim().split(/\r?\n/).length;
        }
        let safeContent = '';
if(Array.isArray(progress.result)) {
  safeContent = progress.result.join('\n');
} else if(typeof progress.result === 'string') {
  safeContent = progress.result;
}
safeContent = safeContent.replace(/</g, '&lt;').replace(/>/g, '&gt;');
const escapedContent = safeContent.replace(/\\/g, "\\\\").replace(/`/g, "\\`").replace(/\$\{/g, "\\${}");
const index = window.contentStore.push(safeContent) - 1;
const link = `<a href="#" onclick="showContentPopup(${index}, '')">Show results</a>`;
breadcrumb = `Found ${count} item${count !== 1 ? 's' : ''} (${link})`;
        break;
      }
      case "search_text": {
        let count = 0;
        if(Array.isArray(progress.result)) {
          count = progress.result.length;
        } else if(typeof progress.result === 'string') {
          count = progress.result.trim() === '' ? 0 : progress.result.trim().split(/\r?\n/).length;
        }
        let safeContent = '';
if(Array.isArray(progress.result)) {
  safeContent = progress.result.join('\n');
} else if(typeof progress.result === 'string') {
  safeContent = progress.result;
}
safeContent = safeContent.replace(/</g, '&lt;').replace(/>/g, '&gt;');
const escapedContent = safeContent.replace(/\\/g, "\\\\").replace(/`/g, "\\`").replace(/\$\{/g, "\\${}");
const index = window.contentStore.push(safeContent) - 1;
const link = `<a href="#" onclick="showContentPopup(${index}, '')">Show results</a>`;
breadcrumb = `Found ${count} match${count !== 1 ? 'es' : ''} (${link})`;
        break;
      }
      case "bash_exec":
        breadcrumb = "Finished running command"; break;
      case "fetch_url":
        breadcrumb = `Finished fetching URL &gt; ${args.url}`; break;
      case "ask_user":
        breadcrumb = "User input finished"; break;
      default:
        breadcrumb = `[${progress.tool}] finished &gt; ` + Object.entries(args).map(([k,v])=>`${k}: ${v}`).join(", ");
    }
  }
  return breadcrumb;
}
