/*
  home.js
  -------
  Powers the homepage (index.html):
    1. Three tabs: Admin | Employee | Customer. The Customer tab also has a
       "Create account" form (POST /auth/register).
    2. Login (POST /auth/login) -> saves the token, redirects to the
       dashboard that matches the role the server returns.
  The chat widget is in chat.js.
*/

const TABS = ["admin", "employee", "customer"];
let activeRole = "admin";
let customerMode = "login"; // "login" | "register"

function switchTab(role) {
  activeRole = role;
  TABS.forEach(t => document.getElementById("tab-" + t).classList.toggle("active", t === role));
  document.querySelector(".login-tabs").style.setProperty("--idx", TABS.indexOf(role));
  setError("");

  const isCustomer = role === "customer";
  document.getElementById("mode-switch").hidden = !isCustomer;
  if (isCustomer) {
    setCustomerMode(customerMode);
  } else {
    showForm("login-form");
    document.getElementById("login-label").textContent = "Username";
    document.getElementById("username").autocomplete = "username";
    document.getElementById("login-hint").textContent =
      "Staff sign in here - you'll land on the right dashboard automatically.";
  }
}

function setCustomerMode(mode) {
  customerMode = mode;
  document.getElementById("mode-login").classList.toggle("active", mode === "login");
  document.getElementById("mode-register").classList.toggle("active", mode === "register");
  setError("");
  if (mode === "login") {
    showForm("login-form");
    document.getElementById("login-label").textContent = "Email or mobile number";
    document.getElementById("username").autocomplete = "email";
    document.getElementById("login-hint").textContent =
      "New here? Choose \"Create account\" - it takes under a minute, no verification needed.";
  } else {
    showForm("register-form");
    document.getElementById("login-hint").textContent =
      "Members earn loyalty points, see their purchase history and unlock members-only offers.";
  }
}

function showForm(id) {
  ["login-form", "register-form"].forEach(f => {
    const el = document.getElementById(f);
    const show = f === id;
    if (show && el.hidden) { el.hidden = false; }      // un-hide -> CSS fade-up replays
    if (!show) el.hidden = true;
  });
}

function setError(message) {
  document.getElementById("login-error").textContent = message;
  document.getElementById("register-error").textContent = message;
}

function goToDashboard(data) {
  saveSession(data.access_token, data.role, data.full_name);
  const target = { admin: "/admin/dashboard", employee: "/employee/dashboard", customer: "/customer/dashboard" };
  window.location.href = target[data.role] || "/";
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json();
}

async function handleLogin(event) {
  event.preventDefault();
  const button = event.target.querySelector("button[type=submit]");
  setError("");
  setLoading(button, true);
  try {
    const data = await postJson("/auth/login", {
      username: document.getElementById("username").value.trim(),
      password: document.getElementById("password").value,
    });

    // Keep the tabs honest: customers and staff each use their own tab.
    if (activeRole === "customer" && data.role !== "customer") {
      throw new Error("That's a staff account - please use the Admin or Employee tab.");
    }
    if (activeRole !== "customer" && data.role === "customer") {
      throw new Error("That's a customer account - please use the Customer tab.");
    }
    goToDashboard(data);
  } catch (err) {
    setError(err.message || "Something went wrong. Please try again.");
    setLoading(button, false);
  }
}

async function handleRegister(event) {
  event.preventDefault();
  const button = event.target.querySelector("button[type=submit]");
  setError("");

  const password = document.getElementById("reg-password").value;
  if (password !== document.getElementById("reg-confirm").value) {
    return setError("Passwords do not match");
  }
  setLoading(button, true);
  try {
    const data = await postJson("/auth/register", {
      full_name: document.getElementById("reg-name").value.trim(),
      mobile_number: document.getElementById("reg-mobile").value.trim(),
      email: document.getElementById("reg-email").value.trim(),
      password,
      confirm_password: document.getElementById("reg-confirm").value,
    });
    goToDashboard(data);
  } catch (err) {
    setError(err.message || "Something went wrong. Please try again.");
    setLoading(button, false);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("login-form").addEventListener("submit", handleLogin);
  document.getElementById("register-form").addEventListener("submit", handleRegister);
  switchTab("admin");
});
