const messagesEl = document.getElementById("messages");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const apiBaseInput = document.getElementById("apiBase");
const sessionIdInput = document.getElementById("sessionId");

const STORED_SESSION_KEY = "carecompass_demo_session_id";

function createSessionId() {
  return `demo-${Math.random().toString(36).slice(2, 10)}`;
}

function getSessionId() {
  const existing = localStorage.getItem(STORED_SESSION_KEY);
  if (existing) {
    return existing;
  }

  const fresh = createSessionId();
  localStorage.setItem(STORED_SESSION_KEY, fresh);
  return fresh;
}

function addMessage(type, text) {
  const el = document.createElement("div");
  el.className = `msg ${type}`;
  el.textContent = text;
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function sendMessage(message) {
  const apiBase = apiBaseInput.value.replace(/\/$/, "");
  const sessionId = sessionIdInput.value.trim();

  const response = await fetch(`${apiBase}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sessionId,
      message,
      context: {
        anonymous: true,
      },
    }),
  });

  if (!response.ok) {
    throw new Error(`API request failed (${response.status})`);
  }

  return response.json();
}

function setBusy(isBusy) {
  sendBtn.disabled = isBusy;
  messageInput.disabled = isBusy;
}

sessionIdInput.value = getSessionId();
addMessage("system", "Connected. Ask a question to preview the prototype.");

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();

  if (!message) {
    return;
  }

  addMessage("user", message);
  messageInput.value = "";
  setBusy(true);

  try {
    const data = await sendMessage(message);
    addMessage("bot", data.reply || "No reply returned.");

    if (Array.isArray(data.options) && data.options.length) {
      addMessage("system", `Options: ${data.options.join(" | ")}`);
    }

    if (data.safety?.recommendHotline) {
      addMessage("system", "Safety flag raised: recommend hotline guidance.");
    }
  } catch (error) {
    addMessage("system", `Error: ${error.message}`);
  } finally {
    setBusy(false);
    messageInput.focus();
  }
});
