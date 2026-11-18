/*
  auth.js
  -------
  Shared helpers used by every page:
    - saveSession()/getToken()/getRole()/logout() -> wrap localStorage
    - apiFetch()  -> a fetch() wrapper that automatically attaches the
      "Authorization: Bearer <token>" header and redirects to "/" if the
      server says the session is no longer valid (401).

  Every dashboard script (admin.js, employee.js, customer.js) calls apiFetch()
  instead of the raw fetch() so login is handled consistently in one place.

  Also here:
    - esc()        -> escapes text before it is put into innerHTML. Customers
                      can now register themselves, so their names/emails must
                      never be inserted into a page as raw HTML.
    - apiBlob()    -> fetches a file (PDF / QR image) with the login token.
    - animateAll() -> count-up animation for numbers marked with data-count.
    - setLoading() -> spinner state for buttons while a request runs.
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
  if (!res.ok) throw new Error(await errorMessage(res));
  if (res.status === 204) return null;
  return res.json();
}

// Turns a failed response into readable text (FastAPI sends `detail` as a
// string for our errors, or as a list for automatic validation errors).
async function errorMessage(res) {
  const err = await res.json().catch(() => ({ detail: res.statusText }));
  if (Array.isArray(err.detail)) {
    return err.detail.map(d => (d.msg || "").replace(/^Value error, /, "")).join(". ") || "Please check the form";
  }
  return err.detail || "Request failed";
}

// Download a protected file (PDF, QR image) and return it as a Blob.
async function apiBlob(url) {
  const res = await fetch(url, { headers: { Authorization: "Bearer " + getToken() } });
  if (res.status === 401) { logout(); throw new Error("Session expired"); }
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.blob();
}

// Which roles may open which dashboard page. Real security is enforced by
// the API (403 for wrong roles) - this just sends people to the right place.
function guardPage(requiredRole) {
  const role = getRole();
  const allowed = {
    admin: ["admin"],
    employee: ["employee", "admin"],
    customer: ["customer"],
  }[requiredRole] || [];
  if (!getToken() || !allowed.includes(role)) {
    window.location.href = "/";
  }
}

// Escape user-supplied text before using it inside innerHTML.
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]
  ));
}

function setLoading(button, isLoading) {
  if (!button) return;
  button.classList.toggle("loading", isLoading);
  button.disabled = isLoading;
}

// Count-up animation: <div data-count="1250.5" data-decimals="2" data-prefix="Rs. ">
function animateAll(root = document) {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  root.querySelectorAll("[data-count]").forEach(el => {
    const target = parseFloat(el.dataset.count) || 0;
    const decimals = parseInt(el.dataset.decimals || "0", 10);
    const prefix = el.dataset.prefix || "";
    const fmt = v => prefix + v.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
    if (reduce || target === 0) { el.textContent = fmt(target); return; }
    const start = performance.now(), duration = 900;
    const tick = now => {
      const t = Math.min((now - start) / duration, 1);
      el.textContent = fmt(target * (1 - Math.pow(1 - t, 3)));
      if (t < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
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
