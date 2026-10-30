import { api } from "../core/api.js";
import { logout, requireRole } from "../core/auth.js";
import { saveUser } from "../core/session.js";
import {
  closeModal,
  emptyState,
  formatDate,
  formatINR,
  html,
  initials,
  mount,
  openModal,
  qs,
  qsa,
  setBusy,
  toast,
} from "../core/ui.js";

const CART_KEY = "roomoraCart";
const PLACEHOLDER = "https://placehold.co/600x400/e5e1ce/55523f?text=Furniture";

const state = {
  user: await requireRole(["user", "seller", "designer", "admin"]),
  products: [],
  designers: [],
  cart: readCart(),
  selectedDesigner: null,
  reviewTarget: null,
  reviewStars: 0,
};

/* ------------------------------------------------------------------ helpers */
function readCart() {
  try {
    return JSON.parse(localStorage.getItem(CART_KEY)) || [];
  } catch {
    return [];
  }
}

function saveCart() {
  localStorage.setItem(CART_KEY, JSON.stringify(state.cart));
  qs("#cartCount").textContent = state.cart.length;
}

// Product images are either full URLs (Supabase, Unsplash) or files that ship with the site.
const imageOf = (product) => product.image_url || product.image || PLACEHOLDER;

const dateInput = (offsetDays = 0) => {
  const d = new Date(Date.now() + offsetDays * 86400000);
  return d.toISOString().slice(0, 10);
};

function fail(error) {
  toast(error.message || "Something went wrong", "error");
}

/* ------------------------------------------------------------------ products */
async function loadProducts() {
  const grid = qs("#productGrid");
  try {
    state.products = await api("/products?limit=100", { auth: false });
    renderProducts();
  } catch (error) {
    mount(grid, emptyState("⚠️", error.message));
  }
}

function renderProducts() {
  const grid = qs("#productGrid");
  if (!state.products.length) {
    mount(grid, emptyState("🛋️", "No furniture is available yet. Please check back soon."));
    return;
  }
  mount(
    grid,
    html`${state.products.map(
      (p) => html`
        <div class="product-card">
          <img src="${imageOf(p)}" class="product-image" alt="${p.name}">
          <div class="product-content">
            <h3>${p.name}</h3>
            <div class="price">${formatINR(p.price)}</div>
            <button class="add-cart" data-action="add-to-cart" data-id="${p.id}" ${p.stock < 1 ? "disabled" : ""}>
              ${p.stock < 1 ? "Out of Stock" : "Add to Cart"}
            </button>
          </div>
        </div>
      `,
    )}`,
  );
}

// A broken product photo falls back to a placeholder (error events do not bubble, so listen while capturing).
document.addEventListener(
  "error",
  (event) => {
    const img = event.target;
    if (img instanceof HTMLImageElement && img.classList.contains("product-image") && img.src !== PLACEHOLDER) {
      img.src = PLACEHOLDER;
    }
  },
  true,
);

/* ------------------------------------------------------------------ designers */
async function loadDesigners() {
  const grid = qs("#designerGrid");
  try {
    state.designers = await api("/designers", { auth: false });
    if (!state.designers.length) {
      mount(grid, emptyState("🎨", "No designers are available yet."));
      return;
    }
    mount(
      grid,
      html`${state.designers.map(
        (d) => html`
          <div class="designer-card">
            <div class="designer-top">
              <div class="designer-avatar">${initials(d.name)}</div>
              <div>
                <h3>${d.name}</h3>
                <p class="muted">${d.speciality}</p>
              </div>
            </div>
            <div class="designer-price">${formatINR(d.price_per_day)} / day</div>
            <button class="book-button" data-action="book-designer" data-id="${d.id}" ${d.is_available ? "" : "disabled"}>
              ${d.is_available ? "Book Designer" : "Not Available"}
            </button>
          </div>
        `,
      )}`,
    );
  } catch (error) {
    mount(grid, emptyState("⚠️", error.message));
  }
}

function openDesignerBooking(id) {
  state.selectedDesigner = state.designers.find((d) => d.id === Number(id));
  if (!state.selectedDesigner) return;
  qs("#bookingName").value = state.user.name;
  qs("#bookingMobile").value = state.user.mobile;
  qs("#bookingEmail").value = state.user.email;
  qs("#bookingDate").min = dateInput(0);
  qs("#bookingDate").value ||= dateInput(7);
  openModal("designerModal");
}

qs("#designerBookingForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.selectedDesigner) return;
  const done = setBusy(qs("#designerBookingForm button[type=submit]"), "Sending…");
  try {
    await api("/bookings", {
      method: "POST",
      body: {
        designer_id: state.selectedDesigner.id,
        name: qs("#bookingName").value.trim(),
        mobile: qs("#bookingMobile").value.trim(),
        email: qs("#bookingEmail").value.trim(),
        project_type: qs("#bookingProject").value,
        start_date: qs("#bookingDate").value,
        days: Number(qs("#bookingDays").value),
        details: qs("#bookingDetails").value.trim(),
      },
    });
    toast(`Designer request sent to ${state.selectedDesigner.name}. You will be notified when they respond.`, "success");
    closeModal("designerModal");
    qs("#designerBookingForm").reset();
    loadHistory();
  } catch (error) {
    fail(error);
  } finally {
    done();
  }
});

/* ------------------------------------------------------------------ cart */
function addToCart(id) {
  const product = state.products.find((p) => p.id === Number(id));
  if (!product) return;
  state.cart.push({ id: product.id, name: product.name, price: product.price, image: imageOf(product) });
  saveCart();
  toast(`${product.name} added to your cart.`);
}

function renderCart() {
  const container = qs("#cartItems");
  if (!state.cart.length) {
    mount(container, emptyState("🛒", "Your furniture cart is empty."));
    qs("#cartTotal").textContent = "₹0";
    return;
  }
  mount(
    container,
    html`${state.cart.map(
      (item, index) => html`
        <div style="display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid #e4ddd3;">
          <img src="${item.image}" alt="" style="width:70px;height:60px;object-fit:cover;border-radius:10px;">
          <div style="flex:1">
            <strong>${item.name}</strong>
            <p class="muted">${formatINR(item.price)}</p>
          </div>
          <button data-action="remove-from-cart" data-index="${index}" style="border:none;background:none;cursor:pointer;font-size:18px;">🗑️</button>
        </div>
      `,
    )}`,
  );
  qs("#cartTotal").textContent = formatINR(state.cart.reduce((sum, item) => sum + Number(item.price), 0));
}

function openCheckout() {
  if (!state.cart.length) return toast("Your furniture cart is empty.", "error");
  closeModal("cartModal");
  qs("#coName").value ||= state.user.name;
  qs("#coMobile").value ||= state.user.mobile;
  qs("#coEmail").value ||= state.user.email;
  openModal("checkoutModal");
}

qs("#checkoutForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.cart.length) return toast("Your cart is empty.", "error");

  // The same product added twice becomes one line with a quantity. Prices are set by the server.
  const quantities = new Map();
  for (const item of state.cart) quantities.set(item.id, (quantities.get(item.id) || 0) + 1);

  const done = setBusy(qs("#checkoutForm button[type=submit]"), "Placing order…");
  try {
    const order = await api("/orders", {
      method: "POST",
      body: {
        items: [...quantities].map(([product_id, quantity]) => ({ product_id, quantity })),
        full_name: qs("#coName").value.trim(),
        mobile: qs("#coMobile").value.trim(),
        address: `${qs("#coHouse").value.trim()}, ${qs("#coStreet").value.trim()}`,
        city: qs("#coCity").value.trim(),
        pincode: qs("#coPin").value.trim(),
        payment_method: qs("#coPayment").value,
      },
    });
    state.cart = [];
    saveCart();
    closeModal("checkoutModal");
    qs("#checkoutForm").reset();
    toast(`Order #${order.id} placed successfully!`, "success");
    loadHistory();
    loadProducts(); // stock has changed
  } catch (error) {
    fail(error);
  } finally {
    done();
  }
});

/* ------------------------------------------------------------------ profile */
function renderProfile() {
  const u = state.user;
  qs("#profileAvatar").textContent = initials(u.name);
  qs("#profileName").textContent = u.name;
  qs("#profileEmail").textContent = u.email;
  qs("#profileMobile").textContent = u.mobile;
  qs("#profileLocation").textContent = u.location || "Not set";
  qs("#profileSince").textContent = new Date(u.created_at).toLocaleDateString("en-IN", {
    month: "long",
    year: "numeric",
  });
}

function openProfileModal() {
  closeModal("settingsModal");
  qs("#pfName").value = state.user.name;
  qs("#pfEmail").value = state.user.email;
  qs("#pfMobile").value = state.user.mobile;
  qs("#pfLocation").value = state.user.location || "";
  openModal("profileModal");
}

qs("#profileForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const done = setBusy(qs("#profileForm button[type=submit]"), "Saving…");
  try {
    state.user = await api("/auth/me", {
      method: "PATCH",
      body: {
        name: qs("#pfName").value.trim(),
        mobile: qs("#pfMobile").value.trim(),
        location: qs("#pfLocation").value.trim(),
      },
    });
    saveUser(state.user);
    renderProfile();
    closeModal("profileModal");
    toast("Profile updated.", "success");
  } catch (error) {
    fail(error);
  } finally {
    done();
  }
});

qs("#passwordForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (qs("#pwNew").value !== qs("#pwConfirm").value) return toast("The new passwords do not match.", "error");
  const done = setBusy(qs("#passwordForm button[type=submit]"), "Updating…");
  try {
    await api("/auth/change-password", {
      method: "POST",
      body: { current_password: qs("#pwCurrent").value, new_password: qs("#pwNew").value },
    });
    qs("#passwordForm").reset();
    closeModal("passwordModal");
    toast("Password updated.", "success");
  } catch (error) {
    fail(error);
  } finally {
    done();
  }
});

// Notification switches in Settings are saved to the account.
function loadPrefs() {
  const prefs = state.user.notification_prefs || {};
  qsa("[data-pref]").forEach((box) => (box.checked = prefs[box.dataset.pref] !== false));
}

document.addEventListener("change", async (event) => {
  const box = event.target.closest("[data-pref]");
  if (!box) return;
  try {
    state.user = await api("/auth/me", { method: "PATCH", body: { notification_prefs: { [box.dataset.pref]: box.checked } } });
    saveUser(state.user);
  } catch (error) {
    box.checked = !box.checked;
    fail(error);
  }
});

const INFO = {
  help: [
    "Help & Support",
    [
      "Questions about an order? Open Order History in your profile to see where each item is. You can cancel an item until the seller has packed it.",
      "Questions about a designer booking? Designers answer requests from their dashboard, and you are notified when they do.",
      "A support contact channel has not been set up in this version of Roomora AI.",
    ],
  ],
  terms: [
    "Terms & Conditions",
    [
      "Roomora AI connects customers with furniture sellers and independent interior designers.",
      "Prices are set by sellers and confirmed by the server at checkout. Payments are recorded only; no money is charged online in this version.",
      "AI-generated designs are inspirations, not construction drawings or guarantees of how a finished room will look.",
    ],
  ],
};

function showInfo(kind) {
  closeModal("settingsModal");
  const [title, paragraphs] = INFO[kind];
  qs("#infoTitle").textContent = title;
  mount(qs("#infoBody"), html`${paragraphs.map((p) => html`<p>${p}</p>`)}`);
  openModal("infoModal");
}

/* ------------------------------------------------------------------ orders and bookings */
async function loadHistory() {
  const box = qs("#orderHistory");
  try {
    const [orders, bookings, reviews] = await Promise.all([
      api("/orders/mine"),
      api("/bookings/mine"),
      api("/reviews/mine"),
    ]);
    renderHistory(orders, bookings, reviews);
  } catch (error) {
    mount(box, emptyState("⚠️", error.message));
  }
}

function renderHistory(orders, bookings, reviews) {
  const box = qs("#orderHistory");
  if (!orders.length && !bookings.length) {
    mount(box, emptyState("📦", "Your orders will appear here."));
    return;
  }
  const reviewedProducts = new Set(reviews.filter((r) => r.product_id).map((r) => r.product_id));
  const reviewedDesigners = new Set(reviews.filter((r) => r.designer_id).map((r) => r.designer_id));

  mount(
    box,
    html`
      ${orders.length ? html`<h4 class="history-title">Furniture orders</h4>` : ""}
      ${orders.map(
        (o) => html`
          <div class="history-card">
            <div class="history-head">
              <strong>Order #${o.id}</strong>
              <span>${formatDate(o.created_at)} · ${formatINR(o.total_amount)} · ${o.payment_method} · ${o.payment_status}</span>
            </div>
            ${o.items.map(
              (i) => html`
                <div class="history-line">
                  <span class="grow">${i.product_name} × ${i.quantity} — ${formatINR(i.price * i.quantity)}</span>
                  <span class="pill ${i.status}">${i.status}</span>
                  ${i.status === "placed"
                    ? html`<button class="mini-button danger" data-action="cancel-item" data-id="${i.id}">Cancel</button>`
                    : ""}
                  ${i.status === "delivered" && i.product_id && !reviewedProducts.has(i.product_id)
                    ? html`<button class="mini-button" data-action="review" data-kind="product" data-id="${i.product_id}" data-label="${i.product_name}">Write a review</button>`
                    : ""}
                </div>
              `,
            )}
          </div>
        `,
      )}
      ${bookings.length ? html`<h4 class="history-title">Designer bookings</h4>` : ""}
      ${bookings.map(
        (b) => html`
          <div class="history-card">
            <div class="history-head">
              <strong>Booking #${b.id} · ${b.designer_name}</strong>
              <span>${b.project_type} · ${formatDate(b.start_date)} · ${b.days} day(s) · ${formatINR(b.total_amount)}</span>
            </div>
            <div class="history-line">
              <span class="grow">${b.details || "No extra details"}</span>
              <span class="pill ${b.status}">${b.status}</span>
              ${b.status === "completed" && !reviewedDesigners.has(b.designer_id)
                ? html`<button class="mini-button" data-action="review" data-kind="designer" data-id="${b.designer_id}" data-label="${b.designer_name}">Write a review</button>`
                : ""}
            </div>
          </div>
        `,
      )}
    `,
  );
}

async function cancelItem(id) {
  if (!confirm("Cancel this item?")) return;
  try {
    await api(`/orders/items/${id}/cancel`, { method: "PATCH" });
    toast("Item cancelled.", "success");
    loadHistory();
    loadProducts();
  } catch (error) {
    fail(error);
  }
}

/* ------------------------------------------------------------------ reviews */
function paintStars() {
  qsa("#starPicker button").forEach((b) => b.classList.toggle("on", Number(b.dataset.star) <= state.reviewStars));
}

function openReview(target) {
  state.reviewTarget = target;
  state.reviewStars = 0;
  paintStars();
  qs("#reviewHeading").textContent = `Review ${target.label}`;
  qs("#reviewForm").reset();
  openModal("reviewModal");
}

qs("#starPicker").addEventListener("click", (event) => {
  const star = event.target.closest("[data-star]");
  if (star) {
    state.reviewStars = Number(star.dataset.star);
    paintStars();
  }
});

qs("#reviewForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.reviewStars) return toast("Please choose a star rating.", "error");
  const done = setBusy(qs("#reviewForm button[type=submit]"), "Submitting…");
  try {
    await api("/reviews", {
      method: "POST",
      body: {
        [state.reviewTarget.kind === "product" ? "product_id" : "designer_id"]: state.reviewTarget.id,
        rating: state.reviewStars,
        title: qs("#rvTitle").value.trim(),
        body: qs("#rvBody").value.trim(),
      },
    });
    closeModal("reviewModal");
    toast("Thank you for your review!", "success");
    loadHistory();
  } catch (error) {
    fail(error);
  } finally {
    done();
  }
});

/* ------------------------------------------------------------------ saved designs */
async function loadSavedDesigns() {
  const box = qs("#savedDesigns");
  try {
    const designs = await api("/designs/mine");
    if (!designs.length) {
      mount(
        box,
        html`<div style="text-align:center;padding:40px 10px;">
          <div style="font-size:40px">❤️</div>
          <p class="muted">No saved designs yet.</p>
        </div>`,
      );
      return;
    }
    mount(
      box,
      html`${designs.map(
        (d) => html`
          <div class="history-card" style="margin-top:12px">
            <div class="history-head">
              <strong>${d.title}</strong>
              <span>${d.space_type} · ${formatDate(d.created_at)}</span>
            </div>
            <p class="muted" style="font-size:10px">${d.prompt.slice(0, 140)}${d.prompt.length > 140 ? "…" : ""}</p>
            <div class="history-line" style="border-top:none;padding-bottom:0">
              <button class="mini-button" data-action="use-design" data-id="${d.id}">Open</button>
              <button class="mini-button danger" data-action="delete-design" data-id="${d.id}">Delete</button>
            </div>
          </div>
        `,
      )}`,
    );
    box.designs = designs;
  } catch (error) {
    mount(box, emptyState("⚠️", error.message));
  }
}

async function saveDesign() {
  const prompt = qs("#designPrompt").value.trim();
  if (!prompt) return toast("Describe your design first.", "error");
  try {
    await api("/designs", {
      method: "POST",
      body: {
        title: prompt.slice(0, 60),
        prompt,
        space_type: qs("#spaceType").value,
        requirements: window.RoomoraAI?.getRequirements() ?? {},
      },
    });
    toast("Design saved to your Roomora profile.", "success");
    loadSavedDesigns();
  } catch (error) {
    fail(error);
  }
}

function useDesign(id) {
  const design = qs("#savedDesigns").designs?.find((d) => d.id === Number(id));
  if (!design) return;
  qs("#designPrompt").value = design.prompt;
  qs("#spaceType").value = design.space_type;
  window.RoomoraAI?.setRequirements(design.requirements);
  qs("#designPrompt").scrollIntoView({ behavior: "smooth", block: "center" });
  toast("Design loaded. Keep editing it with the AI editor.");
}

async function deleteDesign(id) {
  if (!confirm("Delete this saved design?")) return;
  try {
    await api(`/designs/${id}`, { method: "DELETE" });
    loadSavedDesigns();
  } catch (error) {
    fail(error);
  }
}

/* ------------------------------------------------------------------ AI design area */
qs("#roomImage").addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    const preview = qs("#roomPreview");
    preview.src = e.target.result;
    preview.style.display = "block";
  };
  reader.readAsDataURL(file);
});

function generateDesign() {
  const prompt = qs("#designPrompt").value.trim();
  if (!prompt) return toast("Please describe your design first.", "error");

  const section = qs("#aiResultSection");
  section.style.display = "block";
  section.scrollIntoView({ behavior: "smooth" });
  mount(
    qs("#aiResult"),
    html`<div>
      <div style="font-size:60px;margin-bottom:15px;">✨</div>
      <h2>AI Design Ready</h2>
      <p style="margin-top:10px">Your requested design:</p>
      <p style="margin-top:8px;font-style:italic;">"${prompt}"</p>
    </div>`,
  );
}

/* ------------------------------------------------------------------ one click handler for every data-action */
const scrollTo = (id) => qs(`#${id}`).scrollIntoView({ behavior: "smooth" });

const actions = {
  "add-to-cart": (el) => addToCart(el.dataset.id),
  "remove-from-cart": (el) => {
    state.cart.splice(Number(el.dataset.index), 1);
    saveCart();
    renderCart();
  },
  "open-cart": () => {
    renderCart();
    openModal("cartModal");
  },
  "open-checkout": openCheckout,
  "open-settings": () => {
    loadPrefs();
    openModal("settingsModal");
  },
  "book-designer": (el) => openDesignerBooking(el.dataset.id),
  "select-space": (el) => {
    qs("#spaceType").value = el.dataset.space;
    qs("#designPrompt").focus();
    toast(`${el.dataset.space} selected for your project.`);
  },
  "set-prompt": (el) => {
    qs("#designPrompt").value = el.dataset.prompt;
    qs("#designPrompt").focus();
  },
  generate: generateDesign,
  "save-design": saveDesign,
  "scroll-furniture": () => scrollTo("furniture"),
  "scroll-designers": () => scrollTo("designers"),
  "edit-profile": openProfileModal,
  "change-password": () => {
    closeModal("settingsModal");
    openModal("passwordModal");
  },
  "show-help": () => showInfo("help"),
  "show-terms": () => showInfo("terms"),
  "cancel-item": (el) => cancelItem(el.dataset.id),
  review: (el) => openReview({ kind: el.dataset.kind, id: Number(el.dataset.id), label: el.dataset.label }),
  "use-design": (el) => useDesign(el.dataset.id),
  "delete-design": (el) => deleteDesign(el.dataset.id),
  logout: () => confirm("Are you sure you want to logout?") && logout(),
};

document.addEventListener("click", (event) => {
  const el = event.target.closest("[data-action]");
  if (el && actions[el.dataset.action]) actions[el.dataset.action](el);
});

/* ------------------------------------------------------------------ start */
window.addEventListener("load", () => {
  setTimeout(() => {
    const splash = qs("#splashScreen");
    if (!splash) return;
    splash.style.opacity = "0";
    setTimeout(() => (splash.style.display = "none"), 500);
  }, 2000);
});

saveCart();
renderProfile();
loadProducts();
loadDesigners();
loadHistory();
loadSavedDesigns();
