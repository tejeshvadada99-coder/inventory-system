/*
  auth.js
  -------
  Shared helpers used by every page:
    - saveSession()/getToken()/getRole()/logout() -> wrap localStorage
    - apiFetch()  -> a fetch() wrapper that automatically attaches the
      "Authorization: Bearer <token>" header and redirects to "/" if the
      server says the session is no longer valid (401).

  Every dashboard script (admin.js, employee.js) calls apiFetch() instead
  of the raw fetch() so login is handled consistently in one place.
*/

function saveSession(token, role, fullName) {
  localStorage.setItem("ims_token", token);
  localStorage.setItem("ims_role", role);
  localStorage.setItem("ims_name", fullName);
}

function getToken() { return localStorage.getItem("ims_token"); }
function getRole() { return localStorage.getItem("ims_role"); }
function getName() { return localStorage.getItem("ims_name"); }

function logout() {
  localStorage.removeItem("ims_token");
  localStorage.removeItem("ims_role");
  localStorage.removeItem("ims_name");
  window.location.href = "/";
}

async function apiFetch(url, options = {}) {
  const headers = options.headers || {};
  const token = getToken();
  if (token) headers["Authorization"] = "Bearer " + token;
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(url, { ...options, headers });

  if (res.status === 401) {
    logout();
    throw new Error("Session expired");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  if (res.status === 204) return null;
  return res.json();
}

function guardPage(requiredRole) {
  const role = getRole();
  if (!getToken() || (requiredRole === "admin" && role !== "admin")) {
    window.location.href = "/";
  }
}

function showToast(message, isError = false) {
  let toast = document.getElementById("global-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "global-toast";
    toast.className = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.className = "toast" + (isError ? " error" : "") + " show";
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove("show"), 3000);
}
