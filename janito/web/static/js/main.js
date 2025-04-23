import { createContentModal, showContentPopup, showPopup } from "./modal.js";
import { setupTerminal } from "./terminal.js";
import { sendCommandStream } from "./stream.js";
import { handleToolProgress } from "./toolProgress.js";
import { setupSessionControls } from "./sessionControl.js";

window.contentStore = [];
window.showContentPopup = showContentPopup;
window.showPopup = showPopup;

function updateMessageCount(count) {
  const bar = document.getElementById('message-count-bar');
  if(!bar) return;

  bar.textContent = `Messages:${count}`;

  if(count > 0) {
    bar.style.cursor = 'pointer';
    bar.onclick = async () => {
      try {
        const response = await fetch('/load_conversation');
        const data = await response.json();
        document.getElementById('json-modal-content').textContent = JSON.stringify(data.conversation, null, 2);
        document.getElementById('json-modal').style.display = 'block';

        // Update count based on fetched conversation
        if(Array.isArray(data.conversation)) {
          messageCount = data.conversation.filter(msg => msg.role === 'user' || msg.role === 'assistant').length;
          updateMessageCount(messageCount);

      // Trigger fireworks after message submission
      if (typeof window.launchFireworks === 'function') {
        window.launchFireworks();
      }
        }
      } catch(err) {
        document.getElementById('json-modal-content').textContent = 'Error loading conversation: ' + err;
        document.getElementById('json-modal').style.display = 'block';
      }
    };
  } else {
    bar.style.cursor = 'default';
    bar.onclick = null;
  }
}

let messageCount = 0;

function updateModelName(name) {
  const modelBar = document.getElementById('model-name-bar');
  if(modelBar) {
   modelBar.textContent = ` Model:${name}`;
  }
}


document.addEventListener("DOMContentLoaded", async function() {

  // Fetch config and update model bar
  try {
    const resp = await fetch('/get_config');
    const config = await resp.json();
    updateModelName(config.model || 'unknown');
  } catch (e) {
    updateModelName('unknown');
  }

  // Setup JSON modal toggle
  const msgBar = document.getElementById('message-count-bar');
  const jsonModal = document.getElementById('json-modal');
  const jsonContent = document.getElementById('json-modal-content');

  jsonModal.querySelector('.modal-close').onclick = () => {
    jsonModal.style.display = 'none';
  };

  window.addEventListener('keydown', (e) => {
    if(e.key === 'Escape') jsonModal.style.display = 'none';
  });

  setupSessionControls();
  createContentModal();

  const terminalApi = setupTerminal(async (command) => {

    const trimmed = command.trim();
    if(trimmed.startsWith('/')) {
      if(trimmed === '/continue') {
        try {
          const response = await fetch('/load_conversation');
          const data = await response.json();
          if(data.status === 'ok' && Array.isArray(data.conversation)) {
            messageCount = 0;
            data.conversation.forEach(msg => {
              if(msg.role === 'user' || msg.role === 'assistant') {
                messageCount++;
              }
              if(msg.role === 'user') {
                terminalApi.appendOutput('**You:** ' + msg.content);
              } else if(msg.role === 'assistant') {
                terminalApi.appendOutput('**Assistant:** ' + msg.content);
              }
            });
            updateMessageCount(messageCount);

      // Trigger fireworks after message submission
      if (typeof window.launchFireworks === 'function') {
        window.launchFireworks();
      }
          } else {
            terminalApi.appendOutput('No previous conversation found.');
          }
        } catch(err) {
          terminalApi.appendOutput('Error loading conversation: ' + err);
        }
      } else if(trimmed === '/help') {
        terminalApi.appendOutput(`Available commands:\n/continue - Load the last conversation\n/help - Show this help message`);
      } else {
        terminalApi.appendOutput('Unknown command: ' + trimmed);
      }
      return;
    }

    if(messageCount === 0) {
      try {
        await fetch('/new_conversation', { method: 'POST' });
      } catch(err) {
        console.error('Error starting new conversation:', err);
      }
    }

    await sendCommandStream(command, (data) => {
      console.log('[DEBUG] Received event:', data);
      if(data.type === "content" && data.content) {
        terminalApi.appendOutput(data.content);
      } else if([
        "tool_call",
        "tool_result",
        "info",
        "success",
        "error",
        "stdout",
        "stderr"
      ].includes(data.type)) {
        handleToolProgress(data);
      }
    });

    // Increment message count for user + assistant
    messageCount += 2;
    updateMessageCount(messageCount);

      // Trigger fireworks after message submission
      if (typeof window.launchFireworks === 'function') {
        window.launchFireworks();
      }
  });
});
