/**
 * chatbot.js
 * ----------
 * Handles the floating "Ask about flash floods" widget. Sends the user's
 * text to POST /api/chatbot and renders the rule-based reply from
 * backend/chatbot.py + data/knowledge_base.json.
 */

const chatToggle = document.getElementById("chat-toggle");
const chatPanel = document.getElementById("chat-panel");
const chatClose = document.getElementById("chat-close");
const chatMessages = document.getElementById("chat-messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatSuggestions = document.getElementById("chat-suggestions");

let greeted = false;

function addMessage(text, who) {
  const div = document.createElement("div");
  div.className = "msg " + who;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function openChat() {
  chatPanel.hidden = false;
  chatPanel.classList.add("is-open");
  chatPanel.setAttribute("aria-hidden", "false");
  chatToggle.setAttribute("aria-expanded", "true");
  if (!greeted) {
    greeted = true;
    try {
      const res = await fetch("/api/chatbot/greeting");
      const data = await res.json();
      addMessage(data.reply, "bot");
    } catch {
      addMessage("Hi! Ask me about flash flood prevention, kits, or alerts.", "bot");
    }
  }
  chatInput.focus();
}

function closeChat(event) {
  if (event) event.preventDefault();
  chatPanel.hidden = true;
  chatPanel.classList.remove("is-open");
  chatPanel.setAttribute("aria-hidden", "true");
  chatToggle.setAttribute("aria-expanded", "false");
  chatToggle.focus({ preventScroll: true });
}

// Exposed so app.js can close the chat panel when the user picks a location
// from the map/sidebar while the agent is open (see app.js::selectLocation).
window.closeChatIfOpen = function () {
  if (!chatPanel.hidden) closeChat();
};

chatToggle.addEventListener("click", () => {
  if (chatPanel.hidden) openChat(); else closeChat();
});
chatClose.addEventListener("click", closeChat, { passive: false });
chatClose.addEventListener("pointerdown", (e) => e.stopPropagation());
chatClose.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") closeChat(e);
});
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !chatPanel.hidden) closeChat(e);
});

async function sendMessage(text) {
  if (!text.trim()) return;
  addMessage(text, "user");
  chatInput.value = "";

  const typing = document.createElement("div");
  typing.className = "msg bot";
  typing.textContent = "\u2026";
  chatMessages.appendChild(typing);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  try {
    const res = await fetch("/api/chatbot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();
    typing.textContent = data.reply;
  } catch {
    typing.textContent = "Sorry, I couldn't reach the server just now. Please try again.";
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  sendMessage(chatInput.value);
});

chatSuggestions.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-q]");
  if (btn) sendMessage(btn.dataset.q);
});
