/*
  admin.js
  --------
  Drives the admin dashboard. Structure:
    - guardPage() runs first: kicks non-admins back to "/"
    - showTab()  switches which <section> is visible in the sidebar nav
    - loadX()    functions fetch data via apiFetch() and render <tr> rows
    - form submit handlers create new records, then reload that tab's table

  Every network call goes through apiFetch() (see auth.js) so the JWT is
  attached automatically and a 401 bounces back to the login page.
*/

guardPage("admin");

let categoriesCache = [];

function showTab(name) {
  document.querySelectorAll(".tab-section").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
  document.getElementById("tab-" + name).classList.add("active");
  document.querySelector(`.nav-item[data-tab="${name}"]`).classList.add("active");

  const loaders = {
    overview: loadOverview,
    employees: loadEmployees,
    categories: loadCategories,
    products: loadProducts,
    sales: loadSales,
    offers: loadOffers,
  };
  loaders[name] && loaders[name]();
}

// ---------- Overview ----------
async function loadOverview() {
  const [products, sales, employees] = await Promise.all([
    apiFetch("/admin/products"),
    apiFetch("/admin/sales"),
    apiFetch("/admin/employees"),
  ]);
  const totalRevenue = sales.reduce((sum, s) => sum + s.total_amount, 0);
  const lowStock = products.filter(p => p.quantity_in_stock <= p.reorder_level).length;

  document.getElementById("overview-stats").innerHTML = `
    <div class="stat-card"><div class="num">${products.length}</div><div class="label">Products</div></div>
    <div class="stat-card"><div class="num">${employees.length}</div><div class="label">Employees</div></div>
    <div class="stat-card"><div class="num">${sales.length}</div><div class="label">Bills issued</div></div>
    <div class="stat-card"><div class="num">Rs. ${totalRevenue.toFixed(2)}</div><div class="label">Total revenue</div></div>
    <div class="stat-card"><div class="num">${lowStock}</div><div class="label">Low stock items</div></div>
  `;

  document.getElementById("overview-recent-sales").innerHTML = sales.slice(0, 6).map(s => `
    <tr>
      <td>#${s.id}</td>
      <td>${s.customer.name}</td>
      <td>Rs. ${s.total_amount.toFixed(2)}</td>
      <td>${new Date(s.created_at).toLocaleString()}</td>
    </tr>
  `).join("") || `<tr><td colspan="4">No sales yet.</td></tr>`;
}

// ---------- Employees ----------
async function loadEmployees() {
  const employees = await apiFetch("/admin/employees");
  document.getElementById("employees-table").innerHTML = employees.map(e => `
    <tr>
      <td>${e.full_name}</td>
      <td>${e.username}</td>
      <td>${e.email}</td>
      <td>${e.is_active ? '<span class="badge in">Active</span>' : '<span class="badge low">Disabled</span>'}</td>
      <td>${e.is_active ? `<button class="btn-danger" onclick="deactivateEmployee(${e.id})">Deactivate</button>` : ""}</td>
    </tr>
  `).join("") || `<tr><td colspan="5">No employees yet.</td></tr>`;
}

document.getElementById("employee-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await apiFetch("/admin/employees", {
      method: "POST",
      body: JSON.stringify({
        full_name: document.getElementById("emp-name").value,
        username: document.getElementById("emp-username").value,
        email: document.getElementById("emp-email").value,
        password: document.getElementById("emp-password").value,
        role: "employee",
      }),
    });
    e.target.reset();
    showToast("Employee added");
    loadEmployees();
  } catch (err) { showToast(err.message, true); }
});

async function deactivateEmployee(id) {
  if (!confirm("Deactivate this employee?")) return;
  await apiFetch(`/admin/employees/${id}`, { method: "DELETE" });
  showToast("Employee deactivated");
  loadEmployees();
}

// ---------- Categories ----------
async function loadCategories() {
  categoriesCache = await apiFetch("/admin/categories");
  document.getElementById("categories-table").innerHTML = categoriesCache.map(c => `
    <tr>
      <td>${c.name}</td>
      <td>${c.description || "—"}</td>
      <td><button class="btn-danger" onclick="deleteCategory(${c.id})">Delete</button></td>
    </tr>
  `).join("") || `<tr><td colspan="3">No categories yet.</td></tr>`;

  const select = document.getElementById("prod-category");
  if (select) {
    select.innerHTML = categoriesCache.map(c => `<option value="${c.id}">${c.name}</option>`).join("");
  }
}

document.getElementById("category-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await apiFetch("/admin/categories", {
      method: "POST",
      body: JSON.stringify({
        name: document.getElementById("cat-name").value,
        description: document.getElementById("cat-desc").value || null,
      }),
    });
    e.target.reset();
    showToast("Category added");
    loadCategories();
  } catch (err) { showToast(err.message, true); }
});

async function deleteCategory(id) {
  if (!confirm("Delete this category?")) return;
  try {
    await apiFetch(`/admin/categories/${id}`, { method: "DELETE" });
    showToast("Category deleted");
    loadCategories();
  } catch (err) { showToast(err.message, true); }
}

// ---------- Products ----------
async function loadProducts() {
  if (categoriesCache.length === 0) await loadCategories();
  const products = await apiFetch("/admin/products");
  const catName = (id) => (categoriesCache.find(c => c.id === id) || {}).name || "—";

  document.getElementById("products-table").innerHTML = products.map(p => {
    const low = p.quantity_in_stock <= p.reorder_level;
    return `
      <tr>
        <td>${p.name}</td>
        <td class="mono">${p.sku}</td>
        <td>${catName(p.category_id)}</td>
        <td>Rs. ${p.price.toFixed(2)}</td>
        <td><span class="badge ${low ? 'low' : 'in'}">${p.quantity_in_stock} ${low ? '(low)' : ''}</span></td>
        <td><button class="btn-danger" onclick="deleteProduct(${p.id})">Delete</button></td>
      </tr>`;
  }).join("") || `<tr><td colspan="6">No products yet.</td></tr>`;
}

document.getElementById("product-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await apiFetch("/admin/products", {
      method: "POST",
      body: JSON.stringify({
        name: document.getElementById("prod-name").value,
        sku: document.getElementById("prod-sku").value,
        category_id: parseInt(document.getElementById("prod-category").value),
        price: parseFloat(document.getElementById("prod-price").value),
        quantity_in_stock: parseInt(document.getElementById("prod-qty").value),
        reorder_level: parseInt(document.getElementById("prod-reorder").value || 5),
      }),
    });
    e.target.reset();
    showToast("Product added");
    loadProducts();
  } catch (err) { showToast(err.message, true); }
});

async function deleteProduct(id) {
  if (!confirm("Delete this product?")) return;
  try {
    await apiFetch(`/admin/products/${id}`, { method: "DELETE" });
    showToast("Product deleted");
    loadProducts();
  } catch (err) { showToast(err.message, true); }
}

// ---------- Sales ----------
async function loadSales() {
  const sales = await apiFetch("/admin/sales");
  document.getElementById("sales-table").innerHTML = sales.map(s => `
    <tr>
      <td>#${s.id}</td>
      <td>${s.customer.name}</td>
      <td>${s.customer.mobile_number}</td>
      <td>${s.sale_lines.length} item(s)</td>
      <td>Rs. ${s.total_amount.toFixed(2)}</td>
      <td>${s.email_sent ? '<span class="badge in">Sent</span>' : '<span class="badge low">No email</span>'}</td>
      <td>${new Date(s.created_at).toLocaleString()}</td>
    </tr>
  `).join("") || `<tr><td colspan="7">No sales yet.</td></tr>`;
}

// ---------- Offers ----------
async function loadOffers() {
  const offers = await apiFetch("/admin/offers");
  document.getElementById("offers-table").innerHTML = offers.map(o => `
    <tr>
      <td>${o.title}</td>
      <td>${o.description}</td>
      <td>${o.active ? '<span class="badge in">Active</span>' : '<span class="badge low">Inactive</span>'}</td>
      <td><button class="btn-danger" onclick="deleteOffer(${o.id})">Delete</button></td>
    </tr>
  `).join("") || `<tr><td colspan="4">No offers yet.</td></tr>`;
}

document.getElementById("offer-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await apiFetch("/admin/offers", {
      method: "POST",
      body: JSON.stringify({
        title: document.getElementById("offer-title").value,
        description: document.getElementById("offer-desc").value,
        active: true,
      }),
    });
    e.target.reset();
    showToast("Offer added");
    loadOffers();
  } catch (err) { showToast(err.message, true); }
});

async function deleteOffer(id) {
  if (!confirm("Delete this offer?")) return;
  await apiFetch(`/admin/offers/${id}`, { method: "DELETE" });
  showToast("Offer deleted");
  loadOffers();
}

// ---------- Init ----------
document.addEventListener("DOMContentLoaded", loadOverview);
