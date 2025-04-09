export function createContentModal() {
  if (document.getElementById("content-modal")) return;
  const modal = document.createElement("div");
  modal.id = "content-modal";
  Object.assign(modal.style, {
    display: "none",
    position: "fixed",
    top: "0",
    left: "0",
    width: "100%",
    height: "100%",
    backgroundColor: "rgba(0,0,0,0.5)",
    zIndex: "1000"
  });
  modal.innerHTML = `
    <div class="modal-content">
      <div class="modal-header">
        <span class="modal-title">File Content</span>
        <button class="modal-close">&times;</button>
      </div>
      <pre id="modal-content-text" style="white-space: pre-wrap;"></pre>
    </div>`;
  document.body.appendChild(modal);

  modal.querySelector(".modal-close").onclick = () => { modal.style.display = "none"; };
  document.addEventListener("keydown", function(event) {
    if(event.key === "Escape") {
      modal.style.display = "none";
    }
  });
}

export function showContentPopup(index, language) {
  const content = window.contentStore[index];
  const pre = document.getElementById("modal-content-text");
  pre.innerHTML = `<code class="language-${language || ""}"></code>`;
  const codeEl = pre.querySelector("code");

  const lines = content.split('\n');
  const numberedHtml = lines.map((line, idx) => {
    const lineNumber = idx + 1;
    return `<span class="line"><span class="line-number">${lineNumber}</span> ${line}</span>`;
  }).join('\n');

  codeEl.innerHTML = numberedHtml;
  Prism.highlightElement(codeEl);
  document.getElementById("content-modal").style.display = "block";
}

export function showPopup(content) {
  document.getElementById("modal-content-text").textContent = content;
  document.getElementById("content-modal").style.display = "block";
}
