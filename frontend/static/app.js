"use strict";

const connectionStatus = document.getElementById("connectionStatus");
const retryConnection = document.getElementById("retryConnection");
const toolsList = document.getElementById("toolsList");
const toolCount = document.getElementById("toolCount");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const conversation = document.getElementById("conversation");
const attachPdfButton = document.getElementById("attachPdfButton");
const pdfInput = document.getElementById("pdfInput");
const selectedPdfStatus = document.getElementById("selectedPdfStatus");
const selectedPdfName = document.getElementById("selectedPdfName");
const removePdfButton = document.getElementById("removePdfButton");
const MAX_PDF_BYTES = 10 * 1024 * 1024;
let selectedPdf = null;

function setConnectionStatus(state, label) {
  connectionStatus.dataset.state = state;
  connectionStatus.textContent = label;
}

async function checkConnection() {
  setConnectionStatus("checking", "Checking local API…");
  try {
    const response = await fetch("/health", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("Health check failed.");
    const result = await response.json();
    if (result.status !== "ok") throw new Error("API did not report ready.");
    setConnectionStatus("online", "Backend online");
  } catch (_error) {
    setConnectionStatus("offline", "Backend offline");
  }
}

function makeToolCard(tool) {
  const card = document.createElement("article");
  card.className = "tool-card";

  const titleRow = document.createElement("div");
  titleRow.className = "tool-title-row";
  const title = document.createElement("h3");
  title.textContent = String(tool.name || "Unnamed tool");
  titleRow.append(title);

  const description = document.createElement("p");
  description.className = "tool-description";
  description.textContent = String(tool.description || "No description provided.");

  const metadata = document.createElement("div");
  metadata.className = "tool-meta";
  const risk = document.createElement("span");
  risk.className = "meta-chip";
  risk.textContent = `Risk: ${String(tool.risk || "unknown")}`;
  const approval = document.createElement("span");
  approval.className = tool.requires_approval ? "meta-chip approval" : "meta-chip";
  approval.textContent = tool.requires_approval ? "Approval required" : "No approval required";
  metadata.append(risk, approval);

  card.append(titleRow, description, metadata);
  return card;
}

async function loadTools() {
  toolsList.replaceChildren();
  const loading = document.createElement("p");
  loading.className = "muted-message";
  loading.textContent = "Loading local tools…";
  toolsList.append(loading);

  try {
    const response = await fetch("/tools", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("Could not load tools.");
    const tools = await response.json();
    if (!Array.isArray(tools)) throw new Error("Tool list was not valid.");
    toolCount.textContent = String(tools.length);
    toolsList.replaceChildren();
    if (tools.length === 0) {
      const empty = document.createElement("p");
      empty.className = "muted-message";
      empty.textContent = "No tools are currently registered.";
      toolsList.append(empty);
      return;
    }
    tools.forEach((tool) => toolsList.append(makeToolCard(tool)));
  } catch (_error) {
    toolCount.textContent = "—";
    toolsList.replaceChildren();
    const error = document.createElement("p");
    error.className = "muted-message";
    error.textContent = "Could not load tools. Check that the local API is running.";
    toolsList.append(error);
  }
}

function appendMessage(role, text) {
  const isUser = role === "user";
  const article = document.createElement("article");
  article.className = isUser ? "message user-message" : "message assistant-message";

  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = isUser ? "Y" : "L";

  const content = document.createElement("div");
  content.className = "message-content";
  const label = document.createElement("p");
  label.className = "message-label";
  label.textContent = isUser ? "You" : "LEGO AI Agent";

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  bubble.append(paragraph);
  content.append(label, bubble);
  article.append(avatar, content);
  conversation.append(article);
  conversation.scrollTop = conversation.scrollHeight;
}

function clearPdfSelection() {
  selectedPdf = null;
  pdfInput.value = "";
  selectedPdfName.textContent = "";
  selectedPdfStatus.hidden = true;
}

attachPdfButton.addEventListener("click", () => pdfInput.click());
removePdfButton.addEventListener("click", clearPdfSelection);
pdfInput.addEventListener("change", () => {
  const file = pdfInput.files && pdfInput.files[0];
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    clearPdfSelection();
    appendMessage("assistant", "Please choose a PDF file.");
    return;
  }
  if (file.size > MAX_PDF_BYTES) {
    clearPdfSelection();
    appendMessage("assistant", "That PDF exceeds the 10 MiB limit.");
    return;
  }
  selectedPdf = file;
  selectedPdfName.textContent = `${file.name} · ${Math.max(1, Math.ceil(file.size / 1024))} KiB`;
  selectedPdfStatus.hidden = false;
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  const attachment = selectedPdf;
  if (!message || message.length > 4000 || sendButton.disabled) return;

  const displayedMessage = attachment
    ? `${message}\n\nAttached PDF: ${attachment.name}`
    : message;
  appendMessage("user", displayedMessage);
  messageInput.value = "";
  sendButton.disabled = true;
  sendButton.querySelector("span").textContent = attachment ? "Reading…" : "Thinking…";
  try {
    const response = attachment
      ? await fetch(`/chat/pdf`, {
          method: "POST",
          headers: {
            "Content-Type": "application/pdf",
            "X-Chat-Message": message,
            Accept: "application/json",
          },
          body: attachment,
        })
      : await fetch("/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({ message }),
        });
    const result = await response.json();
    if (!response.ok) {
      const detail = typeof result.detail === "string" ? result.detail : "Local chat failed.";
      throw new Error(detail);
    }
    appendMessage("assistant", String(result.reply || "The local model returned an empty reply."));
    if (attachment && selectedPdf === attachment) clearPdfSelection();
  } catch (error) {
    const detail = error instanceof Error ? error.message : "The local chat request failed.";
    appendMessage("assistant", `I couldn't complete that request. ${detail}`);
    messageInput.value = message;
  } finally {
    sendButton.disabled = false;
    sendButton.querySelector("span").textContent = "Send";
    messageInput.focus();
  }
});

retryConnection.addEventListener("click", checkConnection);
checkConnection();
loadTools();
