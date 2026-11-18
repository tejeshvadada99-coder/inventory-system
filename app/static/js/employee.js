/*
  employee.js
  -----------
  Drives the employee dashboard. The billing flow works like this:
    1. Employee picks a product + quantity, clicks "Add to bill" -> pushed
       into a local `cart` array (kept in the browser, not the server yet).
    2. Employee fills in customer name/mobile/email.
    3. "Generate bill" sends the whole cart + customer info to
       POST /employee/bills in one request. The backend does the real work:
       creates/reuses the customer, deducts stock, awards loyalty points to
       members, builds the QR + PDF, and emails it - then returns the
       finished bill, which we render.

  Faster billing: when the employee leaves the mobile field, we look the
  number up (GET /employee/customers/lookup) and auto-fill name + email.
*/

guardPage("employee");

let productsCache = [];
let cart = []; // { product_id, name, price, quantity }

function showTab(name) {
  document.querySelectorAll(".tab-section").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
  document.getElementById("tab-" + name).classList.add("active");
  document.querySelector(`.nav-item[data-tab="${name}"]`).classList.add("active");

  if (name === "products") loadProducts();
  if (name === "customers") loadCustomers();
}

// ---------- Products ----------
async function loadProducts() {
  productsCache = await apiFetch("/employee/products");

  document.getElementById("products-table").innerHTML = productsCache.map(p => `
    <tr>
      <td>${esc(p.name)}</td>
      <td class="mono">${esc(p.sku)}</td>
      <td>Rs. ${p.price.toFixed(2)}</td>
      <td><span class="badge ${p.quantity_in_stock <= p.reorder_level ? 'low' : 'in'}">${p.quantity_in_stock}</span></td>
    </tr>
  `).join("") || `<tr><td colspan="4">No products yet.</td></tr>`;

  const select = document.getElementById("bill-product");
  select.innerHTML = productsCache.map(p =>
    `<option value="${p.id}">${esc(p.name)} — Rs. ${p.price.toFixed(2)} (${p.quantity_in_stock} in stock)</option>`
  ).join("");
}

// ---------- Customers ----------
async function loadCustomers() {
  const customers = await apiFetch("/employee/customers");
  document.getElementById("customers-table").innerHTML = customers.map(c => `
    <tr>
      <td>${esc(c.name)}</td>
      <td>${esc(c.mobile_number)}</td>
      <td>${esc(c.email) || "—"}</td>
      <td>${c.is_member ? `<span class="badge member">Member</span> <span class="mono">${c.loyalty_points} pts</span>` : '<span class="badge low">No account</span>'}</td>
      <td>${c.is_member ? "" : `<button class="btn-small" data-id="${c.id}" data-email="${esc(c.email)}" onclick="editCustomer(this)">Edit email</button>`}</td>
    </tr>
  `).join("") || `<tr><td colspan="5">No customers yet.</td></tr>`;
}

// Staff can fix the email of a customer who hasn't registered yet. If it matches
// the email they later register with, their old bills link to the new account.
async function editCustomer(button) {
  const id = button.dataset.id;
  const email = prompt("Customer's email address:", button.dataset.email || "");
  if (email === null) return;
  try {
    await apiFetch(`/employee/customers/${id}`, { method: "PUT", body: JSON.stringify({ email: email.trim() }) });
    showToast("Customer updated");
    loadCustomers();
  } catch (err) { showToast(err.message, true); }
}

// ---------- Faster billing: look up a saved customer by mobile ----------
async function lookupCustomer() {
  const mobile = document.getElementById("cust-mobile").value.trim();
  const chip = document.getElementById("member-chip");
  chip.classList.remove("show");
  if (mobile.replace(/\D/g, "").length < 7) return;

  try {
    const c = await apiFetch("/employee/customers/lookup?mobile=" + encodeURIComponent(mobile));
    if (!c) return;
    document.getElementById("cust-name").value = c.name;
    if (c.email) document.getElementById("cust-email").value = c.email;
    chip.innerHTML = c.is_member
      ? `<b>${esc(c.name)}</b> is a member &middot; ${c.loyalty_points} points - this bill will earn more.`
      : `<b>${esc(c.name)}</b> found. Not a member yet - ask them to create an account to earn points.`;
    chip.classList.add("show");
  } catch (err) { /* a failed lookup should never block billing */ }
}

// ---------- Billing cart ----------
function addToCart() {
  const productId = parseInt(document.getElementById("bill-product").value);
  const qty = parseInt(document.getElementById("bill-qty").value);
  const product = productsCache.find(p => p.id === productId);
  if (!product || qty < 1) return;

  const existing = cart.find(item => item.product_id === productId);
  if (existing) {
    existing.quantity += qty;
  } else {
    cart.push({ product_id: productId, name: product.name, price: product.price, quantity: qty });
  }
  renderCart();
}

function removeFromCart(productId) {
  cart = cart.filter(item => item.product_id !== productId);
  renderCart();
}

function renderCart() {
  const cartEl = document.getElementById("bill-cart");
  const totalEl = document.getElementById("bill-total");

  if (cart.length === 0) {
    cartEl.innerHTML = `<p style="color:var(--text-muted); font-size:14px;">No items added yet.</p>`;
    totalEl.textContent = "";
    return;
  }

  cartEl.innerHTML = cart.map(item => `
    <div class="bill-cart-row">
      <span>${esc(item.name)} × ${item.quantity}</span>
      <span>Rs. ${(item.price * item.quantity).toFixed(2)}
        <a href="#" onclick="removeFromCart(${item.product_id}); return false;" style="margin-left:10px; color:var(--rust);">remove</a>
      </span>
    </div>
  `).join("");

  const total = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
  totalEl.textContent = "Total: Rs. " + total.toFixed(2);
}

// ---------- Generate bill ----------
async function generateBill() {
  const name = document.getElementById("cust-name").value.trim();
  const mobile = document.getElementById("cust-mobile").value.trim();
  const email = document.getElementById("cust-email").value.trim();

  if (cart.length === 0) return showToast("Add at least one item first", true);
  if (!name || !mobile) return showToast("Customer name and mobile are required", true);

  try {
    const bill = await apiFetch("/employee/bills", {
      method: "POST",
      body: JSON.stringify({
        customer_name: name,
        customer_mobile: mobile,
        customer_email: email || null,
        items: cart.map(item => ({ product_id: item.product_id, quantity: item.quantity })),
      }),
    });

    document.getElementById("receipt-panel").style.display = "block";
    document.getElementById("receipt-summary").textContent =
      `Receipt #${bill.id} — Rs. ${bill.total_amount.toFixed(2)} for ${bill.customer.name}`
      + (bill.points_earned ? ` · +${bill.points_earned} loyalty points` : "");
    document.getElementById("receipt-qr").src = `/static/qrcodes/bill_${bill.id}.png`;
    document.getElementById("receipt-email-status").textContent = bill.email_sent
      ? `Emailed to ${bill.customer.email}`
      : (email ? "Could not send email — check SMTP settings" : "No email provided — not sent");

    showToast("Bill generated");
    cart = [];
    renderCart();
    document.getElementById("cust-name").value = "";
    document.getElementById("cust-mobile").value = "";
    document.getElementById("cust-email").value = "";
    document.getElementById("member-chip").classList.remove("show");
    loadProducts(); // refresh stock numbers
  } catch (err) {
    showToast(err.message, true);
  }
}

// ---------- Init ----------
document.addEventListener("DOMContentLoaded", () => {
  loadProducts();
  document.getElementById("cust-mobile").addEventListener("change", lookupCustomer);
});
