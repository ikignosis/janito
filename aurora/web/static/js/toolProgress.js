import { formatToolProgress } from "../js/progressFormatter.js";

export function handleToolProgress(progress, terminal) {
  console.debug("[WebClient] Tool progress event:", progress);

  const callId = progress.call_id;
  let container = document.getElementById(`call-${callId}`);
  if (!container) {
    container = document.createElement("div");
    container.id = `call-${callId}`;
    container.className = "breadcrumb-container";
    terminal.appendChild(container);
  }

  const msg = formatToolProgress(progress);
  container.innerHTML += `<div class='breadcrumb-tab'>${msg}</div>`;
}
