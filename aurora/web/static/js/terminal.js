export function setupTerminal(onCommandSubmit) {
  const terminal = document.getElementById("terminal");
  let command = "";

  function isScrolledToBottom(element) {
    return element.scrollHeight - element.clientHeight <= element.scrollTop + 5;
  }

  function scrollToBottom(element) {
    element.scrollTop = element.scrollHeight;
  }

  function appendToTerminal(text) {
    const shouldScroll = isScrolledToBottom(terminal);
    const line = document.createElement("div");
    line.innerHTML = text;
    terminal.appendChild(line);
    if (shouldScroll) scrollToBottom(terminal);
  }

  function appendOutput(content, cssClass = "") {
    const shouldScroll = isScrolledToBottom(terminal);
    let html = "";
    if (typeof content === "string") {
      html = marked.parse(content);
    } else {
      html = "<pre>" + JSON.stringify(content, null, 2) + "</pre>";
    }
    const container = document.createElement("div");
    container.className = "markdown-content " + cssClass;
    container.innerHTML = html;
    terminal.appendChild(container);
    if (shouldScroll) scrollToBottom(terminal);
  }

  const inputContainer = document.getElementById("input-container");
  function updateInputDisplay() {
    inputContainer.innerHTML = '<span class="input-active">' + (command || "&nbsp;") + '</span><span class="cursor"></span>';
  }
  updateInputDisplay();

  document.addEventListener("keydown", function(event) {
    if (event.key === "Backspace") {
      command = command.slice(0, -1);
    } else if (event.key === "Enter") {
      appendToTerminal('<span class="user-input">' + command + '</span>');
      onCommandSubmit(command);
      command = "";
    } else if (event.key.length === 1) {
      command += event.key;
    }
    updateInputDisplay();
  });

  return { appendToTerminal, appendOutput };
}
