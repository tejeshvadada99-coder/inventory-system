/*
  customer.js
  -----------
  Drives the customer dashboard (customer_dashboard.html).
    - guardPage("customer") sends anyone who isn't a signed-in customer home.
    - showTab() switches sections and loads that section's data.
    - Every request goes through apiFetch()/apiBlob() so the login token is
      attached automatically. A customer can only ever fetch their own data
      (the server filters everything by the logged-in user).
*/

guardPage("customer");

let profile = null;
const loaded = {};   // remembers which tabs already fetched their data

function showTab(name) {
  document.querySelectorAll(".tab-section").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
  document.getElementById("tab-" + name).classList.add("active");
  document.querySelector(`.nav-item[data-tab="${name}"]`).classList.add("active");

  if (name === "purchases") loadBills();
  if (name === "rewards") loadRewards();
  if (name === "profile") fillProfile();
}

const money = n => "Rs. " + Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const tierBadge = tier => `<span class="badge ${tier.toLowerCase()}">${esc(tier)}</span>`;

// ---------- Overview ----------
async function loadOverview() {
  try {
    const [me, bills] = await Promise.all([apiFetch("/customer/me"), apiFetch("/customer/bills")]);
    profile = me;

    document.getElementById("welcome-title").textContent = "Welcome back, " + me.full_name.split(" ")[0];

    document.getElementById("overview-stats").innerHTML = `
      <div class="stat-card"><div class="num grad" data-count="${me.loyalty_points}">0</div><div class="label">Loyalty points</div></div>
      <div class="stat-card"><div class="num">${tierBadge(me.tier)}</div><div class="label">Member tier</div></div>
      <div class="stat-card"><div class="num" data-count="${me.total_spent}" data-decimals="2" data-prefix="Rs. ">0</div><div class="label">Total spent</div></div>
      <div class="stat-card"><div class="num" data-count="${me.bills_count}">0</div><div class="label">Purchases</div></div>`;

    document.getElementById("tier-panel").innerHTML = tierProgressHtml(me);
    animateAll();
    // Let the bar animate from 0 to its width after it is on screen.
    requestAnimationFrame(() => requestAnimationFrame(() => {
      const bar = document.querySelector("#tier-panel .tier-bar > div");
      if (bar) bar.style.width = me.progress + "%";
    }));

    document.getElementById("overview-latest").innerHTML = bills.length
      ? billCardHtml(bills[0], true)
      : `<p class="empty">No purchases yet - your bills will appear here after your first visit.</p>`;
    const latest = document.querySelector("#overview-latest .bill-card");
    if (latest) loadQr(latest.dataset.bill, latest);
  } catch (err) {
    showToast(err.message, true);
  }
}

function tierProgressHtml(me) {
  const note = me.next_tier
    ? `${me.points_to_next} more points to reach <b>${esc(me.next_tier)}</b>`
    : "You've reached the top tier - thank you!";
  return `
    <h3>Tier progress ${tierBadge(me.tier)}</h3>
    <div class="tier-bar"><div></div></div>
    <div class="tier-note">${note}</div>`;
}

// ---------- Purchases ----------
function billCardHtml(b, open = false) {
  const items = b.items.map(i => `
    <tr><td>${esc(i.product_name)}</td><td>${i.quantity}</td><td>${money(i.unit_price)}</td><td>${money(i.line_total)}</td></tr>`).join("");
  return `
    <div class="bill-card ${open ? "open" : ""}" data-bill="${b.id}">
      <button class="bill-head" type="button" onclick="toggleBill(${b.id}, this.parentElement)">
        <span><strong>Receipt #${b.id}</strong><br><span class="sub">${new Date(b.created_at).toLocaleString()}</span></span>
        <span style="text-align:right"><span class="amt">${money(b.total_amount)}</span><br>
          ${b.points_earned ? `<span class="badge in">+${b.points_earned} pts</span>` : ""}</span>
      </button>
      <div class="bill-body"><div class="bill-inner">
        <table><thead><tr><th>Item</th><th>Qty</th><th>Price</th><th>Total</th></tr></thead><tbody>${items}</tbody></table>
        <div class="bill-qr">
          <img alt="Bill QR code" data-qr="${b.id}">
          <button class="btn-small" type="button" onclick="downloadPdf(${b.id})">Download PDF</button>
        </div>
      </div></div>
    </div>`;
}

async function loadBills() {
  const list = document.getElementById("bills-list");
  try {
    const bills = await apiFetch("/customer/bills");
    list.innerHTML = bills.length
      ? bills.map(b => billCardHtml(b)).join("")
      : `<p class="empty">No purchases yet.</p>`;
  } catch (err) { showToast(err.message, true); }
}

// The QR image is protected (needs the login token), so it is fetched with
// apiBlob() the first time a bill card is opened instead of using a plain <img src>.
async function loadQr(id, card) {
  const img = card.querySelector("img[data-qr]");
  if (!img || img.getAttribute("src")) return;
  try { img.src = URL.createObjectURL(await apiBlob(`/customer/bills/${id}/qr`)); }
  catch (err) { showToast(err.message, true); }
}

function toggleBill(id, card) {
  card.classList.toggle("open");
  if (card.classList.contains("open")) loadQr(id, card);
}

async function downloadPdf(id) {
  try {
    const url = URL.createObjectURL(await apiBlob(`/customer/bills/${id}/pdf`));
    const a = document.createElement("a");
    a.href = url; a.download = `receipt_${id}.pdf`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  } catch (err) { showToast(err.message, true); }
}

// ---------- Rewards & offers ----------
async function loadRewards() {
  try {
    const me = profile || await apiFetch("/customer/me");
    document.getElementById("rewards-info").innerHTML = `
      <h3>How points work</h3>
      <p style="color:var(--muted); font-size:14px; margin:8px 0 0;">
        Earn <b style="color:var(--text)">1 point</b> for every ${money(me.spend_per_point)} you spend.
        Silver starts at ${me.silver_points} points and Gold at ${me.gold_points}.
        You have <b style="color:var(--accent)">${me.loyalty_points}</b> points (${esc(me.tier)}).
      </p>`;

    const offers = await apiFetch("/customer/offers");
    document.getElementById("offers-list").innerHTML = offers.length
      ? offers.map((o, i) => `
        <div class="offer-card ${o.members_only ? "members" : ""}" style="animation-delay:${i * 0.06}s">
          <h4>${esc(o.title)} ${o.members_only ? '<span class="badge member">Members only</span>' : ""}</h4>
          <p>${esc(o.description)}</p>
        </div>`).join("")
      : `<p class="empty">No offers right now - check back soon.</p>`;
  } catch (err) { showToast(err.message, true); }
}

// ---------- Profile ----------
function fillProfile() {
  if (!profile) return;
  document.getElementById("pf-name").value = profile.full_name;
  document.getElementById("pf-email").value = profile.email || "";
  document.getElementById("pf-mobile").value = profile.mobile_number;
  document.getElementById("pf-alerts").checked = profile.alerts_enabled;
}

document.getElementById("profile-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const button = document.getElementById("pf-save");
  setLoading(button, true);
  try {
    profile = await apiFetch("/customer/me", {
      method: "PUT",
      body: JSON.stringify({
        full_name: document.getElementById("pf-name").value,
        email: document.getElementById("pf-email").value,
        alerts_enabled: document.getElementById("pf-alerts").checked,
      }),
    });
    localStorage.setItem("ims_name", profile.full_name);
    document.getElementById("welcome-title").textContent = "Welcome back, " + profile.full_name.split(" ")[0];
    showToast("Profile saved");
  } catch (err) { showToast(err.message, true); }
  setLoading(button, false);
});

document.addEventListener("DOMContentLoaded", loadOverview);
