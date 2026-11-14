/*
  employee.js
  -----------
  Drives the employee dashboard. The billing flow works like this:
    1. Employee picks a product + quantity, clicks "Add to bill" -> pushed
       into a local `cart` array (kept in the browser, not the server yet).
    2. Employee fills in customer name/mobile/email.
    3. "Generate bill" sends the whole cart + customer info to
       POST /employee/bills in one request. The backend does the real work:
       creates/reuses the customer, deducts stock, builds the QR + PDF,
       and emails it — then returns the finished bill, which we render.
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
      <td>${p.name}</td>
      <td class="mono">${p.sku}</td>
      <td>Rs. ${p.price.toFixed(2)}</td>
      <td><span class="badge ${p.quantity_in_stock <= p.reorder_level ? 'low' : 'in'}">${p.quantity_in_stock}</span></td>
    </tr>
  `).join("") || `<tr><td colspan="4">No products yet.</td></tr>`;

  const select = document.getElementById("bill-product");
  select.innerHTML = productsCache.map(p =>
    `<option value="${p.id}">${p.name} — Rs. ${p.price.toFixed(2)} (${p.quantity_in_stock} in stock)</option>`
  ).join("");
}

// ---------- Customers ----------
async function loadCustomers() {
  const customers = await apiFetch("/employee/customers");
  document.getElementById("customers-table").innerHTML = customers.map(c => `
    <tr><td>${c.name}</td><td>${c.mobile_number}</td><td>${c.email || "—"}</td></tr>
  `).join("") || `<tr><td colspan="3">No customers yet.</td></tr>`;
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
      <span>${item.name} × ${item.quantity}</span>
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
      `Receipt #${bill.id} — Rs. ${bill.total_amount.toFixed(2)} for ${bill.customer.name}`;
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
    loadProducts(); // refresh stock numbers
  } catch (err) {
    showToast(err.message, true);
  }
}

// ---------- Init ----------
document.addEventListener("DOMContentLoaded", loadProducts);
