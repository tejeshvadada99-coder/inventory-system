/*
  chat.js
  -------
  The chat widget, shared by the homepage and the customer dashboard
  (the HTML lives in templates/_chat_widget.html).

  Guests get public answers. If a customer is signed in, their login token
  is sent with each message and the bot answers personally (points, last
  order, members-only offers). Needs auth.js loaded first.
*/

function isCustomerSignedIn() {
  return !!getToken() && getRole() === "customer";
}

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

  const headers = { "Content-Type": "application/json" };
  if (isCustomerSignedIn()) headers["Authorization"] = "Bearer " + getToken();

  try {
    const res = await fetch("/chat", { method: "POST", headers, body: JSON.stringify({ message: text }) });
    const data = await res.json();
    appendMessage(data.reply || "Sorry, I couldn't understand that.", "bot");
  } catch (err) {
    appendMessage("Sorry, I couldn't reach the server. Please try again.", "bot");
  }
}

function initChat() {
  const member = isCustomerSignedIn();
  document.getElementById("chat-title").textContent = member ? "My Assistant" : "Store Assistant";

  const chips = [
    ["Today's offers", "What are today's offers?"],
    ["Timings", "What are your timings?"],
    ["Check stock", "Is it in stock?"],
  ];
  if (member) chips.unshift(["My points", "How many points do I have?"], ["My last order", "What was my last order?"]);

  const quick = document.getElementById("chat-quick");
  quick.innerHTML = "";
  chips.forEach(([label, question]) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = label;
    b.addEventListener("click", () => sendChat(question));
    quick.appendChild(b);
  });

  document.getElementById("chat-input").addEventListener("keydown", e => { if (e.key === "Enter") sendChat(); });
  appendMessage(
    member
      ? `Hi ${getName().split(" ")[0]}! Ask me about your points, your last order, or members-only offers.`
      : "Hi! Ask me about today's offers, our timings, or product stock.",
    "bot"
  );
}

document.addEventListener("DOMContentLoaded", initChat);
