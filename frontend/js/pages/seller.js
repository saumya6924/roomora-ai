import { api, download } from "../core/api.js";
import { requireRole } from "../core/auth.js";
import { initDashboard, SELLER_STYLE } from "../core/dashboard.js";
import { initNotifications } from "../core/notifications.js";
import { saveUser } from "../core/session.js";
import {
  capitalize,
  categoryIcon,
  closeModal,
  compactINR,
  emptyRow,
  emptyState,
  formatDate,
  formatINR,
  growthNote,
  html,
  initials,
  liveSearch,
  mount,
  openModal,
  qs,
  qsa,
  setBusy,
  stars,
  timeAgo,
  toast,
} from "../core/ui.js";

const user = await requireRole("seller");
const state = { store: null, products: [], editingId: null, images: [], restockId: null };
const DRAFT_KEY = "roomoraSellerDraft";

const fail = (error) => toast(error.message || "Something went wrong", "error");
const $ = (id) => qs(`#${id}`);
const text = (id, value) => ($(id).textContent = value);

/* ------------------------------------------------------------------ shared lookups */
// Order item statuses use the old panel's four pill colours.
const PILL = { placed: "pending", packed: "processing", shipped: "processing", delivered: "delivered", cancelled: "cancelled" };
const NEXT = {
  placed: ["packed", "shipped", "delivered", "cancelled"],
  packed: ["shipped", "delivered", "cancelled"],
  shipped: ["delivered", "cancelled"],
};
const ACTIVITY_ICON = { order: "📦", review: "⭐", stock: "⚠️", product: "🛋️", payout: "💰", booking: "📅", system: "🔔" };

const pill = (status) => html`<span class="status ${PILL[status] || "pending"}">${capitalize(status)}</span>`;

function stockState(p) {
  if (p.stock <= 0) return { key: "out", label: "Out of Stock", cls: "cancelled" };
  if (p.stock <= p.low_stock_threshold) return { key: "low", label: "Low Stock", cls: "pending" };
  return { key: "ok", label: "Healthy", cls: "delivered" };
}

async function products(force = false) {
  if (force || !state.products.length) state.products = await api("/products/mine");
  return state.products;
}

/* ------------------------------------------------------------------ dashboard */
async function loadDashboard() {
  const d = await api("/sellers/me/dashboard");
  const hour = new Date().getHours();
  text("greeting", `Good ${hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening"}, ${d.store_name}`);
  text("dsProducts", d.total_products);
  text("dsProductsNote", d.products_this_month ? `↑ ${d.products_this_month} this month` : "");
  text("dsOrders", d.total_orders);
  text("dsOrdersNote", growthNote(d.orders_growth));
  text("dsRevenue", compactINR(d.month_revenue));
  text("dsRevenueNote", growthNote(d.revenue_growth));
  text("dsRating", d.review_count ? d.average_rating : "–");
  text("dsRatingNote", d.review_count ? `From ${d.review_count} review${d.review_count > 1 ? "s" : ""}` : "No reviews yet");
  text("dsPending", d.pending_orders);
  text("dsLowStock", d.low_stock);
  text("dsApproval", d.pending_approval);
  text("dsBalance", compactINR(d.available_balance));

  mount(
    $("dsRecentOrders"),
    d.recent_orders.length
      ? html`${d.recent_orders.map(
          (o) => html`<tr>
            <td>#RM${o.order_id}</td><td>${o.customer}</td><td>${o.product}</td>
            <td>${formatINR(o.amount)}</td><td>${pill(o.status)}</td>
          </tr>`,
        )}`
      : emptyRow(5, "No orders yet."),
  );

  mount(
    $("dsTopProducts"),
    d.top_products.length
      ? html`${d.top_products.map(
          (p) => html`<div class="top-product">
            <div class="product-icon">${categoryIcon(p.category)}</div>
            <div><strong>${p.name}</strong><small>${p.sold} sold</small></div>
            <b>${formatINR(p.price)}</b>
          </div>`,
        )}`
      : emptyState("🛋️", "Sales will show up here."),
  );

  mount(
    $("dsActivity"),
    d.activity.length
      ? html`${d.activity.map(
          (a) => html`<div class="activity-item">
            <span>${ACTIVITY_ICON[a.type] || "🔔"}</span>
            <div><strong>${a.title}</strong><small>${a.body} · ${timeAgo(a.created_at)}</small></div>
          </div>`,
        )}`
      : emptyState("🔔", "No activity yet."),
  );

  for (const [key, value] of [["Quality", d.health.product_quality], ["Fulfil", d.health.order_fulfillment], ["Satisfaction", d.health.customer_satisfaction]]) {
    text(`h${key}`, `${value}%`);
    $(`h${key}Bar`).style.width = `${value}%`;
  }
}

/* ------------------------------------------------------------------ products list */
async function loadProducts() {
  mount($("productGrid"), emptyState("⏳", "Loading your products…"));
  try {
    await products(true);
    renderProducts();
  } catch (error) {
    mount($("productGrid"), emptyState("⚠️", error.message));
  }
}

function renderProducts() {
  const search = $("productSearch").value.trim().toLowerCase();
  const category = $("productCategoryFilter").value;
  const status = $("productStatusFilter").value;
  const shown = state.products.filter(
    (p) =>
      (!search || p.name.toLowerCase().includes(search)) &&
      (!category || p.category === category) &&
      (!status || (status === "out" ? p.stock <= 0 : p.status === status)),
  );
  if (!shown.length) {
    mount($("productGrid"), emptyState("🛋️", state.products.length ? "No products match your filters." : "You have not added any products yet."));
    return;
  }
  mount(
    $("productGrid"),
    html`${shown.map((p) => {
      const out = p.stock <= 0;
      const label = out ? "Out of Stock" : p.status === "approved" ? "Active" : capitalize(p.status);
      return html`<div class="product-card" data-name="${p.name}">
        <div class="product-image">
          ${p.image_url ? html`<img src="${p.image_url}" alt="${p.name}">` : categoryIcon(p.category)}
          <span class="product-status ${out || p.status !== "approved" ? "pending" : ""}">${label}</span>
        </div>
        <div class="product-info">
          <span class="category">${p.category}</span>
          <h3>${p.name}</h3>
          <p>${p.short_description}</p>
          <div class="product-bottom"><strong>${formatINR(p.price)}</strong><span>${p.stock} in stock</span></div>
          <div class="product-actions">
            <button data-action="edit-product" data-id="${p.id}">Edit</button>
            <button class="delete-button" data-action="delete-product" data-id="${p.id}">Delete</button>
          </div>
        </div>
      </div>`;
    })}`,
  );
}

["productSearch", "productCategoryFilter", "productStatusFilter"].forEach((id) =>
  $(id).addEventListener("input", renderProducts),
);

async function deleteProduct(id) {
  if (!confirm("Delete this product?")) return;
  try {
    await api(`/products/${id}`, { method: "DELETE" });
    toast("Product deleted.", "success");
    loadProducts();
  } catch (error) {
    fail(error);
  }
}

/* ------------------------------------------------------------------ add / edit product */
// [element id, API field, kind]: one table drives filling the form and reading it back.
const FIELDS = [
  ["pName", "name", "text"], ["pCategory", "category", "text"], ["pType", "product_type", "text"],
  ["pShort", "short_description", "text"], ["pDescription", "description", "text"],
  ["pPrice", "price", "num"], ["pMrp", "mrp", "optnum"], ["pGst", "gst_percent", "num"], ["pDiscount", "discount_percent", "zeronum"],
  ["pLength", "length_cm", "optnum"], ["pWidth", "width_cm", "optnum"], ["pHeight", "height_cm", "optnum"], ["pWeight", "weight_kg", "optnum"],
  ["pMaterial", "material", "text"], ["pColor", "color", "text"], ["pFinish", "finish", "text"],
  ["pSeating", "seating_capacity", "text"], ["pFeatures", "key_features", "text"],
  ["pSku", "sku", "optstr"], ["pStock", "stock", "num"], ["pLowStock", "low_stock_threshold", "five"], ["pWarehouse", "warehouse", "text"],
  ["pDelivery", "delivery_time", "text"], ["pShipping", "shipping_charge", "zeronum"], ["pAssembly", "assembly", "text"],
  ["pInstall", "installation_charge", "zeronum"], ["pAreas", "delivery_areas", "text"],
  ["pReturn", "return_period", "text"], ["pWarranty", "warranty", "text"], ["pPolicy", "return_policy", "text"],
];

const READ = {
  text: (v) => v.trim(),
  num: (v) => Number(v),
  optnum: (v) => (v === "" ? null : Number(v)),
  zeronum: (v) => (v === "" ? 0 : Number(v)),
  five: (v) => (v === "" ? 5 : Number(v)),
  optstr: (v) => v.trim() || null,
};

function collectForm() {
  const body = { image_urls: state.images };
  for (const [id, key, kind] of FIELDS) body[key] = READ[kind]($(id).value);
  return body;
}

function fillForm(values) {
  for (const [id, key] of FIELDS) {
    const value = values[key];
    $(id).value = value === null || value === undefined ? "" : String(value);
  }
}

function renderImages() {
  mount(
    $("imagePreview"),
    html`${state.images.map(
      (url, index) => html`<div class="preview-thumb"><img src="${url}" alt="Product photo ${index + 1}"><button type="button" data-action="remove-image" data-index="${index}" aria-label="Remove">✕</button></div>`,
    )}`,
  );
}

function setFormMode(editing) {
  text("formEyebrow", editing ? "EDIT LISTING" : "PRODUCT LISTING");
  text("formTitle", editing ? "Edit Furniture" : "Add New Furniture");
  text("productSubmit", editing ? "Save Changes" : "Submit for Approval");
}

function newProduct() {
  state.editingId = null;
  state.images = [];
  $("productForm").reset();
  $("pGst").value = "12";
  setFormMode(false);
  const draft = localStorage.getItem(DRAFT_KEY);
  if (draft) {
    const saved = JSON.parse(draft);
    state.images = saved.image_urls || [];
    fillForm(saved);
    toast("Your saved draft was restored.");
  }
  renderImages();
  shell.show("addProduct");
}

async function editProduct(id) {
  const product = (await products()).find((p) => p.id === Number(id));
  if (!product) return;
  state.editingId = product.id;
  state.images = product.images.map((i) => i.url);
  if (!state.images.length && product.image_url) state.images = [product.image_url];
  $("productForm").reset();
  fillForm(product);
  renderImages();
  setFormMode(true);
  shell.show("addProduct");
}

$("productImages").addEventListener("change", async (event) => {
  const files = [...event.target.files];
  event.target.value = "";
  if (state.images.length + files.length > 5) return toast("You can upload a maximum of 5 images.", "error");
  for (const file of files) {
    const form = new FormData();
    form.append("file", file);
    try {
      const { url } = await api("/uploads/image", { method: "POST", form });
      state.images.push(url);
      renderImages();
    } catch (error) {
      fail(error);
    }
  }
});

$("imagePreview").addEventListener("click", (event) => {
  const button = event.target.closest('[data-action="remove-image"]');
  if (!button) return;
  state.images.splice(Number(button.dataset.index), 1);
  renderImages();
});

$("productForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const done = setBusy($("productSubmit"), "Saving…");
  try {
    const editing = state.editingId;
    await api(editing ? `/products/${editing}` : "/products", { method: editing ? "PUT" : "POST", body: collectForm() });
    localStorage.removeItem(DRAFT_KEY);
    toast(editing ? "Product updated." : "Product submitted for admin approval.", "success");
    state.editingId = null;
    shell.show("products");
  } catch (error) {
    fail(error);
  } finally {
    done();
  }
});

function saveDraft() {
  localStorage.setItem(DRAFT_KEY, JSON.stringify(collectForm()));
  toast("Draft saved on this device.");
}

/* ------------------------------------------------------------------ orders */
async function loadOrders() {
  mount($("ordersBody"), emptyRow(8, "Loading orders…"));
  try {
    const rows = await api("/orders/seller");
    const count = (...statuses) => rows.filter((r) => statuses.includes(r.status)).length;
    text("osNew", count("placed"));
    text("osProcessing", count("packed"));
    text("osShipped", count("shipped"));
    text("osDelivered", count("delivered"));
    mount(
      $("ordersBody"),
      rows.length
        ? html`${rows.map(
            (r) => html`<tr>
              <td>#RM${r.order_id}</td><td>${r.customer_name}</td><td>${r.product_name}</td><td>${r.quantity}</td>
              <td>${formatINR(r.price * r.quantity)}</td>
              <td class="${r.payment_status === "paid" ? "paid" : ""}">${r.payment_method} · ${capitalize(r.payment_status)}</td>
              <td>${pill(r.status)}</td>
              <td>${NEXT[r.status]
                ? html`<div class="inline-actions">
                    <select class="row-select" id="next-${r.item_id}">${NEXT[r.status].map((s) => html`<option value="${s}">${capitalize(s)}</option>`)}</select>
                    <button class="action-button" data-action="update-order" data-id="${r.item_id}">Update</button>
                  </div>`
                : "—"}</td>
            </tr>`,
          )}`
        : emptyRow(8, "No orders yet. They will appear here when customers buy your products."),
    );
  } catch (error) {
    mount($("ordersBody"), emptyRow(8, error.message));
  }
}

async function updateOrder(id) {
  const status = $(`next-${id}`).value;
  if (status === "cancelled" && !confirm("Cancel this order item? The stock goes back on the shelf.")) return;
  try {
    await api(`/orders/items/${id}/status`, { method: "PATCH", body: { status } });
    toast(`Order item marked as ${status}.`, "success");
    loadOrders();
  } catch (error) {
    fail(error);
  }
}

/* ------------------------------------------------------------------ inventory */
async function loadInventory() {
  mount($("inventoryBody"), emptyRow(7, "Loading inventory…"));
  try {
    const list = await products(true);
    const states = list.map(stockState);
    text("ivTotal", new Intl.NumberFormat("en-IN").format(list.reduce((n, p) => n + p.stock, 0)));
    const healthy = states.filter((s) => s.key === "ok").length;
    text("ivIn", healthy);
    text("ivInNote", list.length ? `${Math.round((100 * healthy) / list.length)}% of products` : "");
    text("ivLow", states.filter((s) => s.key === "low").length);
    text("ivOut", states.filter((s) => s.key === "out").length);
    mount(
      $("inventoryBody"),
      list.length
        ? html`${list.map((p, i) => html`<tr>
            <td>${p.name}</td><td>${p.sku || "–"}</td><td>${p.stock}</td><td>${p.low_stock_threshold}</td>
            <td>${p.warehouse || "–"}</td>
            <td><span class="status ${states[i].cls}">${states[i].label}</span></td>
            <td><button class="action-button" data-action="restock" data-id="${p.id}">Restock</button></td>
          </tr>`)}`
        : emptyRow(7, "Add a product to start tracking stock."),
    );
  } catch (error) {
    mount($("inventoryBody"), emptyRow(7, error.message));
  }
}

function openRestock(id) {
  const product = state.products.find((p) => p.id === Number(id));
  if (!product) return;
  state.restockId = product.id;
  text("restockTitle", `Restock · ${product.name}`);
  $("restockQty").value = product.stock;
  openModal("restockModal");
}

$("restockForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const done = setBusy(qs("#restockForm button[type=submit]"), "Updating…");
  try {
    await api(`/products/${state.restockId}/stock`, { method: "PATCH", body: { stock: Number($("restockQty").value) } });
    closeModal("restockModal");
    toast("Stock updated.", "success");
    loadInventory();
  } catch (error) {
    fail(error);
  } finally {
    done();
  }
});

/* ------------------------------------------------------------------ customers */
async function loadCustomers() {
  mount($("customersBody"), emptyRow(5, "Loading customers…"));
  try {
    const rows = await api("/sellers/me/customers");
    mount(
      $("customersBody"),
      rows.length
        ? html`${rows.map((c) => html`<tr>
            <td><div class="customer"><div class="customer-avatar">${initials(c.name)}</div><strong>${c.name}</strong></div></td>
            <td>${c.email}</td><td>${c.orders}</td><td>${formatINR(c.total_spent)}</td><td>${formatDate(c.last_order)}</td>
          </tr>`)}`
        : emptyRow(5, "Customers who buy your products will appear here."),
    );
  } catch (error) {
    mount($("customersBody"), emptyRow(5, error.message));
  }
}

/* ------------------------------------------------------------------ payments */
async function loadPayments() {
  try {
    const [money, payouts] = await Promise.all([api("/earnings/me"), api("/payouts/mine")]);
    state.available = money.available;
    text("pyTotal", compactINR(money.total_earnings));
    text("pyMonth", compactINR(money.this_month));
    text("pyAvailable", compactINR(money.available));
    text("pyPending", compactINR(money.pending_payout));
    mount(
      $("payoutsBody"),
      payouts.length
        ? html`${payouts.map((p) => html`<tr>
            <td>${p.reference}</td><td>${formatDate(p.requested_at)}</td><td>${formatINR(p.amount)}</td>
            <td><span class="status ${p.status === "completed" ? "delivered" : p.status === "rejected" ? "cancelled" : "processing"}">${capitalize(p.status)}</span></td>
          </tr>`)}`
        : emptyRow(4, "No payouts yet. Delivered orders add to your available balance."),
    );
  } catch (error) {
    mount($("payoutsBody"), emptyRow(4, error.message));
  }
}

async function requestPayout() {
  if (!state.available) return toast("There is no balance available for payout yet.", "error");
  if (!confirm(`Request a payout of ${formatINR(state.available)}?`)) return;
  try {
    await api("/payouts", { method: "POST", body: {} });
    toast("Payout request submitted.", "success");
    loadPayments();
  } catch (error) {
    fail(error);
  }
}

/* ------------------------------------------------------------------ reviews */
async function loadReviews() {
  try {
    const r = await api("/reviews/received");
    text("rvAverage", r.count ? r.average : "–");
    text("rvStars", stars(Math.round(r.average)));
    text("rvCount", `${r.count} Review${r.count === 1 ? "" : "s"}`);
    mount(
      $("rvBars"),
      html`${[5, 4, 3, 2, 1].map(
        (star) => html`<div class="rating-bar"><span>${star} ★</span><div><div style="width:${r.distribution[star]}%"></div></div><small>${r.distribution[star]}%</small></div>`,
      )}`,
    );
    mount(
      $("rvList"),
      r.reviews.length
        ? html`${r.reviews.map((v) => html`<div class="review-card">
            <div class="review-top">
              <div class="customer-avatar">${initials(v.customer_name)}</div>
              <div><strong>${v.customer_name}</strong><small>${formatDate(v.created_at)}</small></div>
              <span class="stars">${stars(v.rating)}</span>
            </div>
            <h3>${v.title}</h3>
            <p>${v.body}</p>
            <span class="review-product">${v.subject}</span>
          </div>`)}`
        : emptyState("⭐", "Reviews appear here once customers rate delivered products."),
    );
  } catch (error) {
    mount($("rvList"), emptyState("⚠️", error.message));
  }
}

/* ------------------------------------------------------------------ analytics */
async function loadAnalytics() {
  try {
    const a = await api("/sellers/me/analytics");
    const max = Math.max(...a.monthly_sales.map((m) => m.value), 1);
    mount(
      $("anChart"),
      html`${a.monthly_sales.map((m) => {
        const h = Math.max(4, Math.round((100 * m.value) / max));
        return html`<div style="height:${h}%;--bar-height:${h}%" title="${m.label}: ${formatINR(m.value)}"></div>`;
      })}`,
    );
    mount($("anLabels"), html`${a.monthly_sales.map((m) => html`<span>${m.label}</span>`)}`);
    mount(
      $("anCategories"),
      a.categories.length
        ? html`${a.categories.map((c) => html`<div><span>${c.category}</span><strong>${compactINR(c.revenue)}</strong><div class="progress"><div style="width:${c.percent}%"></div></div></div>`)}`
        : emptyState("📈", "Sales by category will appear here."),
    );
  } catch (error) {
    mount($("anCategories"), emptyState("⚠️", error.message));
  }
}

/* ------------------------------------------------------------------ settings and header */
function paintStore(store) {
  state.store = store;
  for (const id of ["storeNameSide", "storeNameTop"]) text(id, store.store_name);
  for (const id of ["storeInitials", "storeInitialsTop"]) text(id, initials(store.store_name));
}

async function loadSettings() {
  try {
    const store = await api("/sellers/me");
    paintStore(store);
    $("stName").value = store.store_name;
    $("stEmail").value = store.business_email;
    $("stMobile").value = store.mobile;
    $("stGst").value = store.gst_number;
    qsa("[data-pref]").forEach((box) => (box.checked = store.notification_prefs[box.dataset.pref] !== false));
  } catch (error) {
    fail(error);
  }
}

$("storeForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const done = setBusy(qs("#storeForm button[type=submit]"), "Saving…");
  try {
    const store = await api("/sellers/me", {
      method: "PUT",
      body: { store_name: $("stName").value.trim(), business_email: $("stEmail").value.trim(), mobile: $("stMobile").value.trim(), gst_number: $("stGst").value.trim() },
    });
    paintStore(store);
    toast("Store information saved.", "success");
  } catch (error) {
    fail(error);
  } finally {
    done();
  }
});

document.addEventListener("change", async (event) => {
  const box = event.target.closest("[data-pref]");
  if (!box) return;
  try {
    saveUser(await api("/auth/me", { method: "PATCH", body: { notification_prefs: { [box.dataset.pref]: box.checked } } }));
  } catch (error) {
    box.checked = !box.checked;
    fail(error);
  }
});

/* ------------------------------------------------------------------ wiring */
const LOADERS = {
  dashboard: loadDashboard,
  products: loadProducts,
  orders: loadOrders,
  inventory: loadInventory,
  customers: loadCustomers,
  payments: loadPayments,
  reviews: loadReviews,
  analytics: loadAnalytics,
  settings: loadSettings,
};

const actions = {
  "new-product": newProduct,
  "edit-product": (el) => editProduct(el.dataset.id),
  "delete-product": (el) => deleteProduct(el.dataset.id),
  "save-draft": saveDraft,
  "update-order": (el) => updateOrder(el.dataset.id),
  restock: (el) => openRestock(el.dataset.id),
  "request-payout": requestPayout,
  "export-orders": () => download("/sellers/me/export/orders.csv", "orders.csv").catch(fail),
};

document.addEventListener("click", (event) => {
  const el = event.target.closest("[data-action]");
  if (el && actions[el.dataset.action]) actions[el.dataset.action](el);
});

const shell = initDashboard(user, {
  style: SELLER_STYLE,
  onShow: (id) => {
    if (id === "addProduct" && state.editingId === null && !$("pName").value) setFormMode(false);
    LOADERS[id]?.().catch(fail);
  },
});
liveSearch($("topSearch"), ".section.active");
initNotifications();
api("/sellers/me").then(paintStore).catch(fail);
