/*
  home.js
  -------
  Powers the homepage (index.html):
    1. Login form -> calls POST /auth/login, saves the token, redirects
       to /admin/dashboard or /employee/dashboard based on the role returned.
    2. Chat widget -> calls POST /chat for every message the customer sends
       (this endpoint is public — no login needed).
*/

// ---------- Login ----------
let activeRole = "admin";

function switchTab(role) {
  activeRole = role;
  document.getElementById("tab-admin").classList.toggle("active", role === "admin");
  document.getElementById("tab-employee").classList.toggle("active", role === "employee");
  document.getElementById("login-error").textContent = "";
}

async function handleLogin(event) {
  event.preventDefault();
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;
  const errorEl = document.getElementById("login-error");
  errorEl.textContent = "";

  try {
    const res = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(err.detail);
    }
    const data = await res.json();

    // Guard: someone logging in on the "Employee" tab shouldn't land in
    // the admin dashboard just because their account happens to be admin.
    if (activeRole === "employee" && data.role === "admin") {
      // admins are allowed to use employee tools too, so let it through
    }

    saveSession(data.access_token, data.role, data.full_name);
    window.location.href = data.role === "admin" ? "/admin/dashboard" : "/employee/dashboard";
  } catch (err) {
    errorEl.textContent = err.message || "Something went wrong. Please try again.";
  }
}

// ---------- Chat widget ----------
function toggleChat() {
  document.getElementById("chat-window").classList.toggle("open");
}

function appendMessage(text, from) {
  const body = document.getElementById("chat-body");
  const div = document.createElement("div");
  div.className = "msg " + from;
  div.textContent = text;
  body.appendChild(div);
  body.scrollTop = body.scrollHeight;
}

async function sendChat(presetText) {
  const input = document.getElementById("chat-input");
  const text = presetText || input.value.trim();
  if (!text) return;

  appendMessage(text, "user");
  input.value = "";

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();
    appendMessage(data.reply, "bot");
  } catch (err) {
    appendMessage("Sorry, I couldn't reach the server. Please try again.", "bot");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("login-form").addEventListener("submit", handleLogin);
  document.getElementById("chat-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendChat();
  });
  appendMessage("Hi! Ask me about today's offers, our timings, or product stock.", "bot");
});
