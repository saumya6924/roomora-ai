import { api, download } from "../core/api.js";
import { requireRole } from "../core/auth.js";
import { ADMIN_STYLE, initDashboard } from "../core/dashboard.js";
import { initNotifications } from "../core/notifications.js";
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
  setBusy,
  timeAgo,
  toast,
} from "../core/ui.js";

const user = await requireRole("admin");
const state = { users: [], products: [], designers: [], transactions: [], bookings: [], sellers: [], promote: null };

const fail = (error) => toast(error.message || "Something went wrong", "error");
const $ = (id) => qs(`#${id}`);
const text = (id, value) => ($(id).textContent = value);

/* ------------------------------------------------------------------ small helpers */
// The admin stylesheet knows these pill colours: active/approved/delivered, pending, inactive/blocked/rejected, processing, booked.
const PILL = {
  delivered: "delivered", completed: "delivered", accepted: "approved", approved: "approved", active: "active",
  pending: "pending", placed: "pending", processing: "processing", requested: "pending",
  cancelled: "blocked", declined: "rejected", rejected: "rejected", blocked: "blocked", suspended: "blocked",
  inactive: "inactive", booked: "booked", offline: "inactive", available: "active",
};
const pill = (status, label = capitalize(status)) => html`<span class="status ${PILL[status] || "pending"}">${label}</span>`;
const lastActive = (when) => (when ? timeAgo(when) : "Never");
const shortDate = (when) => new Date(when).toLocaleDateString("en-IN", { day: "numeric", month: "short" });

function detail(title, rows, extra = "") {
  text("detailTitle", title);
  mount(
    $("detailBody"),
    html`<div class="detail-list">${rows.map(([label, value]) => html`<p><span>${label}</span><strong>${value}</strong></p>`)}</div>${extra}`,
  );
  openModal("detailModal");
}

/* ------------------------------------------------------------------ dashboard */
async function loadDashboard() {
  const d = await api("/admin/dashboard");
  const n = (v) => new Intl.NumberFormat("en-IN").format(v);
  text("dsUsers", n(d.total_users));
  text("dsUsersNote", growthNote(d.users_growth, "this month"));
  text("dsActive", n(d.active_users));
  text("dsActiveNote", `${d.active_percent}% active`);
  text("dsProducts", n(d.total_products));
  text("dsProductsNote", `${d.products_pending} pending approval`);
  text("dsDesigners", n(d.total_designers));
  text("dsDesignersNote", `${d.designers_available} available`);
  text("dsRevenue", compactINR(d.month_revenue));
  text("dsRevenueNote", growthNote(d.revenue_growth, "from last month"));
  text("dsOrders", n(d.total_orders));
  text("dsOrdersNote", growthNote(d.orders_growth, "this month"));
  text("dsPending", d.pending_requests);
  text("dsSellers", d.total_sellers);
  text("dsSellersNote", `${d.sellers_active} active`);
  text("qaRequests", `${d.pending_requests} waiting for review`);
  setRequestCount(d.pending_requests);

  mount(
    $("dsRecent"),
    d.recent_orders.length
      ? html`${d.recent_orders.map(
          (o) => html`<tr><td>${o.ref}</td><td>${o.customer}</td>
            <td><span class="type ${o.kind.toLowerCase()}">${o.kind}</span></td>
            <td>${formatINR(o.amount)}</td><td>${pill(o.status)}</td><td>${shortDate(o.created_at)}</td></tr>`,
        )}`
      : emptyRow(6, "No orders yet."),
  );

  const a = d.activity_today;
  mount(
    $("dsActivity"),
    html`
      <div class="activity-item"><div class="activity-icon">👤</div><div><strong>${a.new_users} new user${a.new_users === 1 ? "" : "s"} registered</strong><small>Today</small></div></div>
      <div class="activity-item"><div class="activity-icon">🛋️</div><div><strong>${a.products_added} furniture product${a.products_added === 1 ? "" : "s"} added</strong><small>Today</small></div></div>
      <div class="activity-item"><div class="activity-icon">🎨</div><div><strong>${a.designer_requests} designer request${a.designer_requests === 1 ? "" : "s"} received</strong><small>Today</small></div></div>
      <div class="activity-item"><div class="activity-icon">💳</div><div><strong>${formatINR(a.revenue)} in orders today</strong><small>Today</small></div></div>`,
  );
  text("sysDatabase", capitalize(d.system.database));
  text("sysAi", d.system.ai_engine === "claude" ? "Claude connected" : "Built-in rules engine");
}

function setRequestCount(count) {
  const badge = $("requestCount");
  badge.textContent = count;
  badge.style.display = count ? "" : "none";
}

/* ------------------------------------------------------------------ users */
async function loadUsers() {
  mount($("usersBody"), emptyRow(8, "Loading users…"));
  try {
    const role = $("userRoleFilter").value;
    state.users = await api(`/admin/users${role ? `?role=${role}` : ""}`);
    renderUsers();
  } catch (error) {
    mount($("usersBody"), emptyRow(8, error.message));
  }
}

function renderUsers() {
  const needle = $("userSearch").value.trim().toLowerCase();
  const status = $("userStatusFilter").value;
  const shown = state.users.filter(
    (u) => (status === "all" || u.status === status) && (!needle || `${u.name} ${u.email}`.toLowerCase().includes(needle)),
  );
  mount(
    $("usersBody"),
    shown.length
      ? html`${shown.map(
          (u) => html`<tr>
            <td><div class="table-user"><div class="user-avatar">${initials(u.name)}</div><strong>${u.name}</strong></div></td>
            <td>${u.email}</td><td>${u.mobile}</td><td>${capitalize(u.role)}</td><td>${u.orders}</td>
            <td>${lastActive(u.last_active)}</td><td>${pill(u.status)}</td>
            <td><button class="table-action" data-action="view-user" data-id="${u.id}">View</button></td>
          </tr>`,
        )}`
      : emptyRow(8, "No users match your filters."),
  );
}

["userSearch", "userStatusFilter"].forEach((id) => $(id).addEventListener("input", renderUsers));
$("userRoleFilter").addEventListener("change", loadUsers);

function viewUser(id) {
  const u = state.users.find((x) => x.id === Number(id));
  if (!u) return;
  const roles = ["user", "seller", "designer", "admin"];
  detail(
    u.name,
    [["Email", u.email], ["Mobile", u.mobile], ["Role", capitalize(u.role)], ["Status", capitalize(u.status)],
     ["Orders & bookings", u.orders], ["Last active", lastActive(u.last_active)], ["Joined", formatDate(u.created_at)]],
    html`<div class="form-group" style="margin-top:14px"><label>Change role</label>
        <select id="roleSelect">${roles.map((r) => html`<option value="${r}" ${r === u.role ? "selected" : ""}>${capitalize(r)}</option>`)}</select></div>
      <button class="primary-button" data-action="save-role" data-id="${u.id}">Save Role</button>
      <button class="primary-button" style="margin-top:8px;background:#a87569" data-action="block-user" data-id="${u.id}">${u.is_active ? "Block User" : "Unblock User"}</button>`,
  );
}

async function saveRole(id) {
  try {
    await api(`/admin/users/${id}/role`, { method: "PATCH", body: { role: $("roleSelect").value } });
    closeModal("detailModal");
    toast("Role updated.", "success");
    loadUsers();
  } catch (error) {
    fail(error);
  }
}

async function blockUser(id) {
  try {
    const result = await api(`/admin/users/${id}/block`, { method: "PATCH" });
    closeModal("detailModal");
    toast(result.is_active ? "User unblocked." : "User blocked.", "success");
    loadUsers();
  } catch (error) {
    fail(error);
  }
}

/* ------------------------------------------------------------------ furniture */
async function loadProducts() {
  mount($("productsBody"), emptyRow(7, "Loading products…"));
  try {
    state.products = await api("/admin/products");
    const list = state.products;
    text("fuTotal", list.length);
    text("fuApproved", list.filter((p) => p.status === "approved").length);
    text("fuPending", list.filter((p) => p.status === "pending").length);
    text("fuOut", list.filter((p) => p.stock <= 0).length);
    renderProducts();
  } catch (error) {
    mount($("productsBody"), emptyRow(7, error.message));
  }
}

function renderProducts() {
  const needle = $("productSearch").value.trim().toLowerCase();
  const category = $("productCategoryFilter").value;
  const status = $("productStatusFilter").value;
  const shown = state.products.filter(
    (p) => (!needle || p.name.toLowerCase().includes(needle)) && (!category || p.category === category) && (!status || p.status === status),
  );
  mount(
    $("productsBody"),
    shown.length
      ? html`${shown.map(
          (p) => html`<tr>
            <td><div class="product-table"><div class="product-mini-image">${p.image_url ? html`<img src="${p.image_url}" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:inherit">` : categoryIcon(p.category)}</div><strong>${p.name}</strong></div></td>
            <td>${p.seller_name}</td><td>${p.category}</td><td>${formatINR(p.price)}</td><td>${p.stock}</td>
            <td>${pill(p.status)}</td>
            <td><div class="inline-actions">
              ${p.status !== "approved" ? html`<button class="table-action approve" data-action="product-status" data-id="${p.id}" data-status="approved">Approve</button>` : ""}
              ${p.status !== "rejected" ? html`<button class="table-action danger-action" data-action="product-status" data-id="${p.id}" data-status="rejected">Reject</button>` : ""}
            </div></td>
          </tr>`,
        )}`
      : emptyRow(7, "No products match your filters."),
  );
}

["productSearch", "productCategoryFilter", "productStatusFilter"].forEach((id) => $(id).addEventListener("input", renderProducts));

async function setProductStatus(id, status) {
  try {
    await api(`/products/${id}/status`, { method: "PATCH", body: { status } });
    toast(status === "approved" ? "Furniture product approved successfully." : "Product rejected.", "success");
    loadProducts();
  } catch (error) {
    fail(error);
  }
}

$("productForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const done = setBusy(qs("#productForm button[type=submit]"), "Adding…");
  try {
    const image = $("apImage").value.trim();
    await api("/products", {
      method: "POST",
      body: {
        name: $("apName").value.trim(), category: $("apCategory").value, short_description: $("apShort").value.trim(),
        price: Number($("apPrice").value), stock: Number($("apStock").value), image_urls: image ? [image] : [],
      },
    });
    closeModal("productModal");
    $("productForm").reset();
    toast("Product added and approved.", "success");
    loadProducts();
  } catch (error) {
    fail(error);
  } finally {
    done();
  }
});

/* ------------------------------------------------------------------ designers */
const AVAILABILITY = { available: "Available", booked: "Booked", offline: "Offline" };

async function loadDesigners() {
  mount($("designerGrid"), emptyState("⏳", "Loading designers…"));
  try {
    state.designers = await api("/admin/designers");
    mount(
      $("designerGrid"),
      state.designers.length
        ? html`${state.designers.map((d) => {
            const live = d.status === "approved";
            const [cls, label] = live ? [d.availability, AVAILABILITY[d.availability]] : [d.status, d.status === "pending" ? "Pending approval" : "Suspended"];
            return html`<div class="designer-admin-card">
              <div class="designer-admin-top">
                <div class="large-designer-avatar">${initials(d.name)}</div>
                <div><h3>${d.name}</h3><p>${d.title || d.speciality}</p>${pill(cls, label)}</div>
              </div>
              <div class="designer-details">
                <div><span>Price / Day</span><strong>${formatINR(d.price_per_day)}</strong></div>
                <div><span>Projects</span><strong>${d.projects}</strong></div>
                <div><span>Rating</span><strong>${d.review_count ? `${d.rating} ★` : "–"}</strong></div>
              </div>
              <div class="designer-actions">
                <button class="table-action" data-action="view-designer" data-id="${d.id}">View Profile</button>
                <button class="table-action ${d.status === "approved" ? "danger-action" : "approve"}" data-action="designer-status" data-id="${d.id}" data-status="${d.status === "approved" ? "suspended" : "approved"}">${d.status === "approved" ? "Suspend" : d.status === "pending" ? "Approve" : "Reactivate"}</button>
              </div>
            </div>`;
          })}`
        : emptyState("🎨", "No designers yet. Use “+ Add Designer” to create one."),
    );
  } catch (error) {
    mount($("designerGrid"), emptyState("⚠️", error.message));
  }
}

function viewDesigner(id) {
  const d = state.designers.find((x) => x.id === Number(id));
  if (!d) return;
  detail(d.name, [
    ["Title", d.title || "–"], ["Speciality", d.speciality || "–"], ["Price / day", formatINR(d.price_per_day)],
    ["Approval", capitalize(d.status)], ["Availability", AVAILABILITY[d.availability]],
    ["Completed projects", d.projects], ["Rating", d.review_count ? `${d.rating} ★ (${d.review_count})` : "No reviews yet"],
  ]);
}

async function setDesignerStatus(id, status) {
  if (!confirm(`${status === "approved" ? "Approve / reactivate" : "Suspend"} this designer?`)) return;
  try {
    await api(`/designers/${id}/status`, { method: "PATCH", body: { status } });
    toast("Designer status updated.", "success");
    loadDesigners();
  } catch (error) {
    fail(error);
  }
}

/* ------------------------------------------------------------------ add designer / seller (promote a customer) */
async function openPromote(kind) {
  state.promote = kind;
  text("promoteTitle", kind === "designer" ? "Add Designer" : "Add Seller");
  $("pmDesignerFields").style.display = kind === "designer" ? "block" : "none";
  try {
    const customers = await api("/admin/users?role=user");
    if (!customers.length) return toast("There are no customer accounts to promote. Ask the person to sign up first.", "error");
    mount($("pmUser"), html`${customers.map((u) => html`<option value="${u.id}">${u.name} · ${u.email}</option>`)}`);
    openModal("promoteModal");
  } catch (error) {
    fail(error);
  }
}

$("promoteForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const id = Number($("pmUser").value);
  const done = setBusy(qs("#promoteForm button[type=submit]"), "Saving…");
  try {
    if (state.promote === "designer") {
      await api("/designers", { method: "POST", body: { user_id: id, speciality: $("pmSpeciality").value.trim(), price_per_day: Number($("pmPrice").value) } });
      loadDesigners();
    } else {
      await api(`/admin/users/${id}/role`, { method: "PATCH", body: { role: "seller" } });
      loadSellers();
    }
    closeModal("promoteModal");
    toast(state.promote === "designer" ? "Designer added." : "Seller added.", "success");
  } catch (error) {
    fail(error);
  } finally {
    done();
  }
});

/* ------------------------------------------------------------------ orders */
async function loadOrders() {
  mount($("ordersBody"), emptyRow(8, "Loading orders…"));
  try {
    state.transactions = await api("/admin/transactions");
    const t = state.transactions;
    const today = new Date().toDateString();
    text("orToday", t.filter((o) => new Date(o.created_at).toDateString() === today).length);
    text("orProcessing", t.filter((o) => ["processing", "accepted"].includes(o.status)).length);
    text("orDelivered", t.filter((o) => ["delivered", "completed"].includes(o.status)).length);
    text("orCancelled", t.filter((o) => ["cancelled", "declined"].includes(o.status)).length);
    mount(
      $("ordersBody"),
      t.length
        ? html`${t.map(
            (o) => html`<tr>
              <td>${o.ref}</td><td>${o.customer}</td><td>${o.kind}</td><td>${o.item}</td><td>${formatINR(o.amount)}</td>
              <td><span class="${o.payment === "paid" ? "paid" : ""}">${capitalize(o.payment)}</span></td>
              <td>${pill(o.status)}</td>
              <td><button class="table-action" data-action="view-order" data-ref="${o.ref}">View</button></td>
            </tr>`,
          )}`
        : emptyRow(8, "No orders or bookings yet."),
    );
  } catch (error) {
    mount($("ordersBody"), emptyRow(8, error.message));
  }
}

function viewOrder(ref) {
  const o = state.transactions.find((x) => x.ref === ref);
  if (!o) return;
  detail(`Order ${o.ref}`, [
    ["Type", o.kind], ["Customer", o.customer], ["Item / designer", o.item], ["Amount", formatINR(o.amount)],
    ["Payment", capitalize(o.payment)], ["Status", capitalize(o.status)], ["Placed", formatDate(o.created_at)],
  ]);
}

/* ------------------------------------------------------------------ designer requests */
async function loadRequests() {
  mount($("requestGrid"), emptyState("⏳", "Loading requests…"));
  try {
    state.bookings = await api("/admin/bookings");
    const pending = state.bookings.filter((b) => b.status === "pending").length;
    setRequestCount(pending);
    mount(
      $("requestGrid"),
      state.bookings.length
        ? html`${state.bookings.map(
            (b) => html`<div class="request-admin-card">
              <div class="request-header">${pill(b.status)}<small>${b.ref}</small></div>
              <div class="request-user"><div class="user-avatar">${initials(b.customer)}</div><div><strong>${b.customer}</strong><p>${b.project_type}</p></div></div>
              <div class="request-designer"><span>Requested Designer</span><strong>${b.designer}</strong></div>
              <div class="request-details">
                <div><span>Start Date</span><strong>${formatDate(b.start_date)}</strong></div>
                <div><span>Duration</span><strong>${b.days} Day${b.days === 1 ? "" : "s"}</strong></div>
                <div><span>Value</span><strong>${formatINR(b.amount)}</strong></div>
              </div>
              ${b.status === "pending"
                ? html`<div class="request-actions">
                    <button class="approve-button" data-action="booking-status" data-id="${b.id}" data-status="accepted">Approve</button>
                    <button class="reject-button" data-action="booking-status" data-id="${b.id}" data-status="declined">Reject</button>
                  </div>`
                : ""}
            </div>`,
          )}`
        : emptyState("🔔", "No designer requests yet."),
    );
  } catch (error) {
    mount($("requestGrid"), emptyState("⚠️", error.message));
  }
}

async function setBookingStatus(id, status) {
  try {
    await api(`/bookings/${id}/status`, { method: "PATCH", body: { status } });
    toast(status === "accepted" ? "Designer request approved. The user will be notified." : "Designer request rejected.", "success");
    loadRequests();
  } catch (error) {
    fail(error);
  }
}

/* ------------------------------------------------------------------ sellers */
async function loadSellers() {
  mount($("sellersBody"), emptyRow(7, "Loading sellers…"));
  try {
    state.sellers = await api("/admin/sellers");
    const s = state.sellers;
    text("seTotal", s.length);
    text("seActive", s.filter((x) => x.status === "active").length);
    text("sePending", s.filter((x) => x.status === "pending").length);
    text("seSuspended", s.filter((x) => x.status === "suspended").length);
    mount(
      $("sellersBody"),
      s.length
        ? html`${s.map(
            (x) => html`<tr>
              <td>${x.owner}</td><td>${x.business}</td><td>${x.products}</td><td>${x.orders}</td><td>${compactINR(x.revenue)}</td>
              <td>${pill(x.status === "pending" ? "pending" : x.status === "suspended" ? "blocked" : "active", x.status === "pending" ? "Verification" : capitalize(x.status))}</td>
              <td><button class="table-action" data-action="view-seller" data-id="${x.user_id}">${x.status === "pending" ? "Review" : "View"}</button></td>
            </tr>`,
          )}`
        : emptyRow(7, "No sellers yet. Use “+ Add Seller” to create one."),
    );
  } catch (error) {
    mount($("sellersBody"), emptyRow(7, error.message));
  }
}

function viewSeller(id) {
  const s = state.sellers.find((x) => x.user_id === Number(id));
  if (!s) return;
  detail(
    s.business,
    [["Owner", s.owner], ["Email", s.email], ["Products", s.products], ["Orders", s.orders], ["Revenue", formatINR(s.revenue)]],
    html`<div class="form-group" style="margin-top:14px"><label>Seller status</label>
        <select id="sellerStatus">${["active", "pending", "suspended"].map((v) => html`<option value="${v}" ${v === s.status ? "selected" : ""}>${capitalize(v)}</option>`)}</select></div>
      <button class="primary-button" data-action="save-seller" data-id="${s.user_id}">Save Status</button>`,
  );
}

async function saveSeller(id) {
  try {
    await api(`/admin/sellers/${id}/status`, { method: "PATCH", body: { status: $("sellerStatus").value } });
    closeModal("detailModal");
    toast("Seller status updated.", "success");
    loadSellers();
  } catch (error) {
    fail(error);
  }
}

/* ------------------------------------------------------------------ reports and payouts */
async function loadReports() {
  try {
    const [r, payouts] = await Promise.all([api("/admin/reports"), api("/admin/payouts")]);
    const max = Math.max(...r.monthly_revenue.map((m) => m.value), 1);
    mount($("rpChart"), html`${r.monthly_revenue.map((m) => html`<div style="height:${Math.max(4, Math.round((100 * m.value) / max))}%" title="${m.label}: ${formatINR(m.value)}"></div>`)}`);
    mount($("rpLabels"), html`${r.monthly_revenue.map((m) => html`<span>${m.label}</span>`)}`);
    text("rpTotal", new Intl.NumberFormat("en-IN").format(r.total_orders));
    text("rpFurniture", r.furniture_percent);
    text("rpDesigner", r.designer_percent);
    const angle = Math.round(r.furniture_percent * 3.6);
    $("rpDonut").style.setProperty("background", `conic-gradient(#85895d 0deg ${angle}deg, #c7bda5 ${angle}deg 360deg)`, "important");

    mount(
      $("payoutsBody"),
      payouts.length
        ? html`${payouts.map(
            (p) => html`<tr>
              <td>${p.reference}</td><td>${p.user_name}</td><td>${capitalize(p.role)}</td><td>${formatINR(p.amount)}</td><td>${formatDate(p.requested_at)}</td>
              <td>${pill(p.status)}</td>
              <td>${["requested", "processing"].includes(p.status)
                ? html`<div class="inline-actions">
                    <select class="row-select" id="payout-${p.id}">
                      ${p.status === "requested" ? html`<option value="processing">Processing</option>` : ""}
                      <option value="completed">Completed</option><option value="rejected">Rejected</option>
                    </select>
                    <button class="table-action" data-action="update-payout" data-id="${p.id}">Update</button>
                  </div>`
                : "—"}</td>
            </tr>`,
          )}`
        : emptyRow(7, "No payout requests yet."),
    );
  } catch (error) {
    mount($("payoutsBody"), emptyRow(7, error.message));
  }
}

async function updatePayout(id) {
  try {
    await api(`/admin/payouts/${id}`, { method: "PATCH", body: { status: $(`payout-${id}`).value } });
    toast("Payout updated.", "success");
    loadReports();
  } catch (error) {
    fail(error);
  }
}

/* ------------------------------------------------------------------ settings */
async function loadSettings() {
  try {
    const flags = await api("/admin/settings");
    document.querySelectorAll("[data-setting]").forEach((box) => (box.checked = !!flags[box.dataset.setting]));
  } catch (error) {
    fail(error);
  }
}

document.addEventListener("change", async (event) => {
  const box = event.target.closest("[data-setting]");
  if (!box) return;
  try {
    await api("/admin/settings", { method: "PUT", body: { [box.dataset.setting]: box.checked } });
    toast("Setting saved.", "success");
  } catch (error) {
    box.checked = !box.checked;
    fail(error);
  }
});

/* ------------------------------------------------------------------ wiring */
const LOADERS = {
  dashboard: loadDashboard,
  users: loadUsers,
  furniture: loadProducts,
  designers: loadDesigners,
  orders: loadOrders,
  requests: loadRequests,
  sellers: loadSellers,
  reports: loadReports,
  settings: loadSettings,
};

const actions = {
  "view-user": (el) => viewUser(el.dataset.id),
  "save-role": (el) => saveRole(el.dataset.id),
  "block-user": (el) => blockUser(el.dataset.id),
  "product-status": (el) => setProductStatus(el.dataset.id, el.dataset.status),
  "add-product": () => openModal("productModal"),
  "view-designer": (el) => viewDesigner(el.dataset.id),
  "designer-status": (el) => setDesignerStatus(el.dataset.id, el.dataset.status),
  "add-designer": () => openPromote("designer"),
  "add-seller": () => openPromote("seller"),
  "view-order": (el) => viewOrder(el.dataset.ref),
  "booking-status": (el) => setBookingStatus(el.dataset.id, el.dataset.status),
  "view-seller": (el) => viewSeller(el.dataset.id),
  "save-seller": (el) => saveSeller(el.dataset.id),
  "update-payout": (el) => updatePayout(el.dataset.id),
  "export-users": () => download("/admin/export/users.csv", "users.csv").catch(fail),
  "export-orders": () => download("/admin/export/orders.csv", "orders.csv").catch(fail),
};

document.addEventListener("click", (event) => {
  const el = event.target.closest("[data-action]");
  if (el && actions[el.dataset.action]) actions[el.dataset.action](el);
});

initDashboard(user, { style: ADMIN_STYLE, onShow: (id) => LOADERS[id]?.().catch(fail) });
liveSearch($("globalSearch"), ".admin-section.active-section");
initNotifications();
