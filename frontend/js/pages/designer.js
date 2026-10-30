import { api } from "../core/api.js";
import { requireRole } from "../core/auth.js";
import { initDashboard, SELLER_STYLE } from "../core/dashboard.js";
import { initNotifications } from "../core/notifications.js";
import { saveUser } from "../core/session.js";
import {
  capitalize,
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

const user = await requireRole("designer");
const state = { me: null, bookings: [], services: [], editingService: null, available: 0 };

const fail = (error) => toast(error.message || "Something went wrong", "error");
const $ = (id) => qs(`#${id}`);
const text = (id, value) => ($(id).textContent = value);

/* ------------------------------------------------------------------ small helpers */
const day = (iso) => new Date(`${iso}T00:00:00`);
const short = (iso) => day(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
const range = (start, days) => {
  const end = new Date(day(start).getTime() + (days - 1) * 86400000);
  const to = end.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  return days > 1 ? `${short(start)} – ${to}` : short(start);
};
const todayIso = () => new Date().toISOString().slice(0, 10);

const NOTE_ICON = { order: "📦", booking: "📩", review: "⭐", product: "🛋️", stock: "⚠️", payout: "💰", system: "🔔" };
const SERVICE_ICON = { RESIDENTIAL: "🏠", COMMERCIAL: "🏢", HOSPITALITY: "☕", CONSULTATION: "💡" };
const PORTFOLIO_ICON = { RESIDENTIAL: "🏠", COMMERCIAL: "☕", BEDROOM: "🛏️", HOSPITALITY: "🏨", OFFICE: "🏢", "LIVING ROOM": "🛋️" };

function bookingPill(b) {
  if (b.status === "completed") return ["delivered", "Completed"];
  if (b.status === "declined") return ["cancelled", "Declined"];
  if (b.status === "accepted") return b.start_date > todayIso() ? ["pending", "Upcoming"] : ["processing", "In Progress"];
  return ["pending", "Pending"];
}

async function bookings(force = false) {
  if (force || !state.bookings.length) state.bookings = await api("/bookings/designer");
  return state.bookings;
}

async function profile(force = false) {
  if (force || !state.me) state.me = await api("/designers/me");
  return state.me;
}

/* ------------------------------------------------------------------ header and availability */
function paintHeader(me) {
  state.me = me;
  text("sideTitle", me.title || "Interior Designer");
  text("topTitle", me.title || "Interior Designer");
  paintAvailability(me.is_available);
}

function paintAvailability(available) {
  $("availabilityToggle").checked = available;
  text("availTitle", available ? "You are currently available for new projects" : "You are hidden from new bookings");
  text("topAvailability", available ? "Available" : "Unavailable");
}

$("availabilityToggle").addEventListener("change", async () => {
  try {
    const result = await api("/designers/me/availability", { method: "PATCH" });
    paintAvailability(result.is_available);
    toast(result.is_available ? "Your designer profile is now available." : "Your profile is hidden from new bookings.");
  } catch (error) {
    $("availabilityToggle").checked = !$("availabilityToggle").checked;
    fail(error);
  }
});

async function refreshBadge() {
  const pending = (await bookings(true)).filter((b) => b.status === "pending").length;
  text("requestBadge", pending || "");
}

/* ------------------------------------------------------------------ dashboard */
async function loadDashboard() {
  const d = await api("/designers/me/dashboard");
  text("greeting", `Welcome back, ${d.name.split(" ")[0]}`);
  text("dsPending", d.pending_requests);
  text("dsActive", d.active_projects);
  text("dsActiveNote", `${d.starting_this_week} this week`);
  text("dsMonth", compactINR(d.month_earnings));
  text("dsMonthNote", growthNote(d.earnings_growth));
  text("dsRating", d.review_count ? d.rating : "–");
  text("dsRatingNote", `${d.review_count} review${d.review_count === 1 ? "" : "s"}`);

  mount(
    $("dsRequests"),
    d.new_requests.length
      ? html`${d.new_requests.map(
          (r) => html`<div class="request-item">
            <div class="client-avatar">${initials(r.client)}</div>
            <div class="request-content"><strong>${r.client}</strong><span>${r.project_type}</span><small>${range(r.start_date, r.days)}${r.location ? " · " + r.location : ""}</small></div>
            <div class="request-price">${formatINR(r.amount)}</div>
            <button class="accept-small" data-section="requests">Review</button>
          </div>`,
        )}`
      : emptyState("📩", "No requests waiting for you."),
  );

  mount(
    $("dsUpcoming"),
    d.upcoming.length
      ? html`${d.upcoming.map(
          (u) => html`<div class="calendar-item">
            <div class="date-box"><strong>${day(u.start_date).getDate()}</strong><span>${day(u.start_date).toLocaleDateString("en-IN", { month: "short" }).toUpperCase()}</span></div>
            <div><strong>${u.project_type}</strong><small>${u.client} · ${u.days} day${u.days > 1 ? "s" : ""}</small></div>
          </div>`,
        )}`
      : emptyState("📅", "Nothing scheduled yet."),
  );

  const p = d.performance;
  text("pfViews", new Intl.NumberFormat("en-IN").format(p.profile_views));
  text("pfRequests", p.booking_requests);
  text("pfConversion", `${p.conversion_rate}%`);
  $("pfViewsBar").style.width = p.profile_views ? "100%" : "0";
  $("pfRequestsBar").style.width = `${p.profile_views ? Math.min(100, Math.round((100 * p.booking_requests) / p.profile_views)) : 0}%`;
  $("pfConversionBar").style.width = `${p.conversion_rate}%`;

  mount(
    $("dsReview"),
    d.recent_review
      ? html`<div class="review-user"><div class="client-avatar">${initials(d.recent_review.customer)}</div><div><strong>${d.recent_review.customer}</strong><small>${timeAgo(d.recent_review.created_at)}</small></div></div>
          <div class="stars">${stars(d.recent_review.rating)}</div>
          <p>${d.recent_review.body ? `"${d.recent_review.body}"` : ""}</p>`
      : emptyState("⭐", "Your latest client review will appear here."),
  );
}

/* ------------------------------------------------------------------ requests */
async function loadRequests() {
  mount($("requestCards"), emptyState("⏳", "Loading requests…"));
  try {
    const pending = (await bookings(true)).filter((b) => b.status === "pending");
    text("requestBadge", pending.length || "");
    mount(
      $("requestCards"),
      pending.length
        ? html`${pending.map(
            (b) => html`<div class="booking-card">
              <div class="booking-header">
                <div class="client-info">
                  <div class="large-avatar">${initials(b.name)}</div>
                  <div><strong>${b.name}</strong><span>${b.email}</span><small>${b.mobile}</small></div>
                </div>
                <span class="status pending">Pending</span>
              </div>
              <div class="booking-details">
                <div><span>PROJECT</span><strong>${b.project_type}</strong></div>
                <div><span>LOCATION</span><strong>${b.location || "–"}</strong></div>
                <div><span>DATES</span><strong>${range(b.start_date, b.days)}</strong></div>
                <div><span>BUDGET</span><strong>${formatINR(b.total_amount)}</strong></div>
              </div>
              <div class="project-description"><span>CLIENT MESSAGE</span><p>${b.details || "No extra details were provided."}</p></div>
              <div class="booking-actions">
                <button class="decline-button" data-action="decline" data-id="${b.id}">Decline</button>
                <button class="secondary-button" data-action="details" data-id="${b.id}">View Details</button>
                <button class="primary-button" data-action="approve" data-id="${b.id}">✓ Approve Request</button>
              </div>
            </div>`,
          )}`
        : emptyState("📩", "No pending requests. New booking requests will appear here."),
    );
  } catch (error) {
    mount($("requestCards"), emptyState("⚠️", error.message));
  }
}

async function answer(id, status) {
  const booking = state.bookings.find((b) => b.id === Number(id));
  const verb = { accepted: "Approve", declined: "Decline", completed: "Mark as completed" }[status];
  if (!confirm(`${verb} booking from ${booking?.name ?? "this client"}?`)) return;
  try {
    await api(`/bookings/${id}/status`, { method: "PATCH", body: { status } });
    toast(status === "declined" ? "Request declined." : status === "accepted" ? `Request approved. ${booking.name} will be notified.` : "Project marked as completed.", "success");
    state.bookings = await api("/bookings/designer");
    const active = qs(".section.active")?.id;
    if (active === "bookings") loadBookings();
    else loadRequests();
    refreshBadge();
  } catch (error) {
    fail(error);
  }
}

function showDetails(id) {
  const b = state.bookings.find((x) => x.id === Number(id));
  if (!b) return;
  text("detailsTitle", `Booking #${b.id}`);
  mount(
    $("detailsBody"),
    html`<div class="detail-list">
      <p><span>Client</span><strong>${b.name}</strong></p>
      <p><span>Email</span><strong>${b.email}</strong></p>
      <p><span>Mobile</span><strong>${b.mobile}</strong></p>
      <p><span>Project</span><strong>${b.project_type}</strong></p>
      <p><span>Location</span><strong>${b.location || "–"}</strong></p>
      <p><span>Dates</span><strong>${range(b.start_date, b.days)} (${b.days} day${b.days > 1 ? "s" : ""})</strong></p>
      <p><span>Value</span><strong>${formatINR(b.total_amount)}</strong></p>
      <p><span>Status</span><strong>${capitalize(b.status)}</strong></p>
      <p><span>Requested</span><strong>${formatDate(b.created_at)}</strong></p>
      <p><span>Message</span><strong style="max-width:230px;text-align:right">${b.details || "–"}</strong></p>
    </div>`,
  );
  openModal("detailsModal");
}

/* ------------------------------------------------------------------ my bookings */
async function loadBookings() {
  mount($("bookingsBody"), emptyRow(7, "Loading bookings…"));
  try {
    const all = (await bookings(true)).filter((b) => b.status !== "pending");
    const accepted = all.filter((b) => b.status === "accepted");
    text("bkActive", accepted.filter((b) => b.start_date <= todayIso()).length);
    text("bkUpcoming", accepted.filter((b) => b.start_date > todayIso()).length);
    text("bkCompleted", all.filter((b) => b.status === "completed").length);
    text("bkTotal", all.filter((b) => b.status !== "declined").length);
    mount(
      $("bookingsBody"),
      all.length
        ? html`${all.map((b) => {
            const [cls, label] = bookingPill(b);
            return html`<tr>
              <td>${b.project_type}</td><td>${b.name}</td><td>${b.location || "–"}</td>
              <td>${range(b.start_date, b.days)}</td><td>${formatINR(b.total_amount)}</td>
              <td><span class="status ${cls}">${label}</span></td>
              <td><div class="inline-actions">
                <button class="action-button" data-action="details" data-id="${b.id}">View</button>
                ${b.status === "accepted" ? html`<button class="action-button" data-action="complete" data-id="${b.id}">Mark Completed</button>` : ""}
              </div></td>
            </tr>`;
          })}`
        : emptyRow(7, "Accepted and completed projects will appear here."),
    );
  } catch (error) {
    mount($("bookingsBody"), emptyRow(7, error.message));
  }
}

/* ------------------------------------------------------------------ portfolio */
async function loadPortfolio() {
  try {
    const items = await api("/designers/me/portfolio");
    mount(
      $("portfolioPreview"),
      items.length
        ? html`${items.map(
            (p) => html`<div class="portfolio-card">
              <div class="portfolio-image">${p.image_url ? html`<img src="${p.image_url}" alt="${p.title}">` : PORTFOLIO_ICON[p.category.toUpperCase()] || "🏠"}</div>
              <div class="portfolio-info">
                <span>${p.category || "PROJECT"}</span>
                <h3>${p.title}</h3>
                <p>${[p.location, p.area_sqft ? `${new Intl.NumberFormat("en-IN").format(p.area_sqft)} sq.ft.` : ""].filter(Boolean).join(" · ")}</p>
                <button class="card-delete" data-action="delete-portfolio" data-id="${p.id}">Remove</button>
              </div>
            </div>`,
          )}`
        : emptyState("🖼️", "Add your first project to showcase your work."),
    );
  } catch (error) {
    mount($("portfolioPreview"), emptyState("⚠️", error.message));
  }
}

$("portfolioForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const done = setBusy(qs("#portfolioForm button[type=submit]"), "Adding…");
  try {
    let image_url = "";
    const file = $("poImage").files[0];
    if (file) {
      const form = new FormData();
      form.append("file", file);
      image_url = (await api("/uploads/image", { method: "POST", form })).url;
    }
    await api("/designers/me/portfolio", {
      method: "POST",
      body: {
        title: $("poTitle").value.trim(),
        category: $("poCategory").value.trim().toUpperCase(),
        location: $("poLocation").value.trim(),
        area_sqft: $("poArea").value ? Number($("poArea").value) : null,
        image_url,
      },
    });
    closeModal("portfolioModal");
    $("portfolioForm").reset();
    toast("Portfolio project added.", "success");
    loadPortfolio();
  } catch (error) {
    fail(error);
  } finally {
    done();
  }
});

async function deletePortfolio(id) {
  if (!confirm("Remove this project from your portfolio?")) return;
  try {
    await api(`/designers/me/portfolio/${id}`, { method: "DELETE" });
    loadPortfolio();
  } catch (error) {
    fail(error);
  }
}

/* ------------------------------------------------------------------ services */
async function loadServices() {
  try {
    state.services = await api("/designers/me/services");
    const me = await profile();
    $("contractTerms").value = me.contract_terms;
    mount(
      $("serviceGrid"),
      state.services.length
        ? html`${state.services.map(
            (s) => html`<div class="service-card">
              <div class="service-icon">${SERVICE_ICON[s.category.toUpperCase()] || "✦"}</div>
              <span>${s.category || "SERVICE"}</span>
              <h3>${s.name}</h3>
              <p>${s.description}</p>
              <div class="service-price"><strong>${formatINR(s.price)}</strong><span>/ ${s.unit}</span></div>
              <button class="service-button" data-action="edit-service" data-id="${s.id}">Edit Service</button>
            </div>`,
          )}`
        : emptyState("✦", "Add the services you offer, with your prices."),
    );
  } catch (error) {
    mount($("serviceGrid"), emptyState("⚠️", error.message));
  }
}

function openService(id) {
  const service = state.services.find((s) => s.id === Number(id));
  state.editingService = service?.id ?? null;
  text("serviceModalTitle", service ? "Edit Service" : "Add Service");
  $("serviceForm").reset();
  if (service) {
    $("svCategory").value = service.category;
    $("svName").value = service.name;
    $("svDescription").value = service.description;
    $("svPrice").value = service.price;
    $("svUnit").value = service.unit;
  }
  $("svDelete").style.display = service ? "block" : "none";
  openModal("serviceModal");
}

$("serviceForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const done = setBusy(qs("#serviceForm button[type=submit]"), "Saving…");
  try {
    const editing = state.editingService;
    await api(editing ? `/designers/me/services/${editing}` : "/designers/me/services", {
      method: editing ? "PUT" : "POST",
      body: {
        category: $("svCategory").value.trim().toUpperCase(),
        name: $("svName").value.trim(),
        description: $("svDescription").value.trim(),
        price: Number($("svPrice").value),
        unit: $("svUnit").value,
      },
    });
    closeModal("serviceModal");
    toast("Service saved.", "success");
    state.me = null;
    loadServices();
  } catch (error) {
    fail(error);
  } finally {
    done();
  }
});

async function deleteService() {
  if (!confirm("Delete this service?")) return;
  try {
    await api(`/designers/me/services/${state.editingService}`, { method: "DELETE" });
    closeModal("serviceModal");
    state.me = null;
    loadServices();
  } catch (error) {
    fail(error);
  }
}

async function saveTerms() {
  try {
    state.me = await api("/designers/me", { method: "PUT", body: { contract_terms: $("contractTerms").value } });
    toast("Contract terms saved.", "success");
  } catch (error) {
    fail(error);
  }
}

/* ------------------------------------------------------------------ earnings */
async function loadEarnings() {
  try {
    const [money, payouts] = await Promise.all([api("/earnings/me"), api("/payouts/mine")]);
    state.available = money.available;
    text("erTotal", compactINR(money.total_earnings));
    text("erMonth", compactINR(money.this_month));
    text("erAvailable", compactINR(money.available));
    text("erPending", compactINR(money.pending_payout + money.pending_earnings));
    mount(
      $("payoutsBody"),
      payouts.length
        ? html`${payouts.map((p) => html`<tr>
            <td>${p.reference}</td><td>${formatDate(p.requested_at)}</td><td>${formatINR(p.amount)}</td>
            <td><span class="status ${p.status === "completed" ? "delivered" : p.status === "rejected" ? "cancelled" : "processing"}">${capitalize(p.status)}</span></td>
          </tr>`)}`
        : emptyRow(4, "No payouts yet. Completed projects add to your available balance."),
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
    toast("Payout request submitted successfully.", "success");
    loadEarnings();
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
        (star) => html`<div><span>${star} ★</span><div class="rating-bar"><div style="width:${r.distribution[star]}%"></div></div><small>${r.distribution[star]}%</small></div>`,
      )}`,
    );
    mount(
      $("rvList"),
      r.reviews.length
        ? html`${r.reviews.map((v) => html`<div class="review-card">
            <div class="review-top">
              <div class="client-avatar">${initials(v.customer_name)}</div>
              <div><strong>${v.customer_name}</strong><small>${formatDate(v.created_at)}</small></div>
              <span class="stars">${stars(v.rating)}</span>
            </div>
            <h3>${v.title}</h3>
            <p>${v.body}</p>
            <span class="review-project">${v.subject}</span>
          </div>`)}`
        : emptyState("⭐", "Reviews appear here once clients rate your completed projects."),
    );
  } catch (error) {
    mount($("rvList"), emptyState("⚠️", error.message));
  }
}

/* ------------------------------------------------------------------ notifications */
let notices;
async function loadNotifications() {
  try {
    const data = await api("/notifications");
    mount(
      $("notificationList"),
      data.items.length
        ? html`${data.items.map(
            (n) => html`<div class="notification-card ${n.is_read ? "" : "unread"}">
              <div class="notification-icon">${NOTE_ICON[n.type] || "🔔"}</div>
              <div><strong>${n.title}</strong><p>${n.body}</p><small>${timeAgo(n.created_at)}</small></div>
            </div>`,
          )}`
        : emptyState("🔔", "You have no notifications yet."),
    );
    notices?.refresh();
  } catch (error) {
    mount($("notificationList"), emptyState("⚠️", error.message));
  }
}

async function markAllRead() {
  try {
    await api("/notifications/read-all", { method: "POST" });
    toast("All notifications marked as read.");
    loadNotifications();
  } catch (error) {
    fail(error);
  }
}

/* ------------------------------------------------------------------ profile */
function paintProfile(me) {
  paintHeader(me);
  text("pfHeadName", me.name);
  text("pfHeadTitle", me.title);
  text("pfHeadLocation", me.location);
  $("pfName").value = me.name;
  $("pfTitle").value = me.title;
  $("pfEmail").value = me.email;
  $("pfMobile").value = me.mobile;
  $("pfExperience").value = me.experience;
  $("pfLocation").value = me.location;
  $("pfAbout").value = me.about;
  $("pfSpeciality").value = me.speciality;
  text("dtExperience", me.experience || "–");
  text("dtProjects", me.projects_completed);
  text("dtRating", me.review_count ? `${me.rating} ★` : "–");
  text("dtRate", me.response_rate === null ? "–" : `${me.response_rate}%`);
  text("dtTime", me.response_hours === null ? "–" : me.response_hours < 1 ? "Under 1 hour" : `About ${Math.round(me.response_hours)} hours`);
  const approved = me.status === "approved";
  text("verifyTitle", approved ? "Verified Designer" : me.status === "pending" ? "Awaiting approval" : "Profile suspended");
  text("verifyText", approved ? "Your professional profile has been approved by Roomora AI." : "Customers cannot find you until an admin approves your profile.");
  text("verifySince", `Member since ${new Date(me.verified_since).toLocaleDateString("en-IN", { month: "long", year: "numeric" })}`);
  $("bkHolder").value = me.bank_holder;
  $("bkAccount").value = me.bank_account_masked;
  $("bkIfsc").value = me.ifsc;
  text("visibilityButton", me.is_visible ? "Hide My Profile" : "Show My Profile");
  qsa("[data-pref]").forEach((box) => (box.checked = me.notification_prefs[box.dataset.pref] ?? box.checked));
}

async function loadProfile() {
  paintProfile(await profile(true));
}

async function saveProfile() {
  try {
    const me = await api("/designers/me", {
      method: "PUT",
      body: {
        name: $("pfName").value.trim(),
        title: $("pfTitle").value.trim(),
        mobile: $("pfMobile").value.trim(),
        experience: $("pfExperience").value,
        location: $("pfLocation").value.trim(),
        about: $("pfAbout").value.trim(),
        speciality: $("pfSpeciality").value.trim(),
      },
    });
    paintProfile(me);
    qsa("[data-user-name]").forEach((el) => (el.textContent = me.name));
    qsa("[data-user-initials]").forEach((el) => (el.textContent = initials(me.name)));
    toast("Professional profile saved successfully.", "success");
  } catch (error) {
    fail(error);
  }
}

/* ------------------------------------------------------------------ settings */
$("passwordForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  if ($("pwNew").value !== $("pwConfirm").value) return toast("The new passwords do not match.", "error");
  const done = setBusy(qs("#passwordForm button[type=submit]"), "Updating…");
  try {
    await api("/auth/change-password", { method: "POST", body: { current_password: $("pwCurrent").value, new_password: $("pwNew").value } });
    $("passwordForm").reset();
    toast("Password updated successfully.", "success");
  } catch (error) {
    fail(error);
  } finally {
    done();
  }
});

$("bankForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    paintProfile(await api("/designers/me", { method: "PUT", body: { bank_holder: $("bkHolder").value.trim(), bank_account_masked: $("bkAccount").value.trim(), ifsc: $("bkIfsc").value.trim() } }));
    toast("Bank details saved.", "success");
  } catch (error) {
    fail(error);
  }
});

async function toggleVisibility() {
  try {
    const me = await profile();
    paintProfile(await api("/designers/me", { method: "PUT", body: { is_visible: !me.is_visible } }));
    toast("Your profile visibility has been updated.");
  } catch (error) {
    fail(error);
  }
}

async function deleteAccount() {
  if (!confirm("Are you sure you want to request account deletion?")) return;
  try {
    await api("/auth/delete-request", { method: "POST" });
    toast("Account deletion request submitted.", "success");
  } catch (error) {
    fail(error);
  }
}

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
  requests: loadRequests,
  bookings: loadBookings,
  portfolio: loadPortfolio,
  services: loadServices,
  earnings: loadEarnings,
  reviews: loadReviews,
  notifications: loadNotifications,
  profile: loadProfile,
  settings: loadProfile,
};

const actions = {
  approve: (el) => answer(el.dataset.id, "accepted"),
  decline: (el) => answer(el.dataset.id, "declined"),
  complete: (el) => answer(el.dataset.id, "completed"),
  details: (el) => showDetails(el.dataset.id),
  "add-portfolio": () => openModal("portfolioModal"),
  "delete-portfolio": (el) => deletePortfolio(el.dataset.id),
  "add-service": () => openService(null),
  "edit-service": (el) => openService(el.dataset.id),
  "delete-service": deleteService,
  "save-terms": saveTerms,
  "request-payout": requestPayout,
  "mark-all-read": markAllRead,
  "save-profile": saveProfile,
  "toggle-visibility": toggleVisibility,
  "delete-account": deleteAccount,
};

document.addEventListener("click", (event) => {
  const el = event.target.closest("[data-action]");
  if (el && actions[el.dataset.action]) actions[el.dataset.action](el);
});

initDashboard(user, { style: SELLER_STYLE, onShow: (id) => LOADERS[id]?.().catch(fail) });
liveSearch($("topSearch"), ".section.active");
notices = await initNotifications();
profile().then(paintHeader).catch(fail);
refreshBadge().catch(() => {});
