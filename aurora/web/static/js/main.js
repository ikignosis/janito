import { createContentModal, showContentPopup, showPopup } from "./modal.js";
import { setupTerminal } from "./terminal.js";
import { sendCommandStream } from "./stream.js";
import { handleToolProgress } from "./toolProgress.js";
import { setupSessionControls } from "../js/sessionControl.js";

window.contentStore = [];
window.showContentPopup = showContentPopup;
window.showPopup = showPopup;

document.addEventListener("DOMContentLoaded", function() {
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
            data.conversation.forEach(msg => {
              if(msg.role === 'user') {
                terminalApi.appendOutput('**You:** ' + msg.content);
              } else if(msg.role === 'assistant') {
                terminalApi.appendOutput('**Assistant:** ' + msg.content);
              }
            });
          } else {
            terminalApi.appendOutput('No previous conversation found.');
          }
        } catch(err) {
          terminalApi.appendOutput('Error loading conversation: ' + err);
        }
      } else {
        terminalApi.appendOutput('Unknown command: ' + trimmed);
      }
      return;
    }

    await sendCommandStream(command, (data) => {
      if(data.type === "content" && data.content) {
        terminalApi.appendOutput(data.content);
      } else if(data.type === "tool_progress") {
        handleToolProgress(data.data, document.getElementById("terminal"));
      } else if(data.type === "error") {
        terminalApi.appendOutput("Error: " + data.error);
      }
    });
  });
});
