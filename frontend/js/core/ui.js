// Small UI helpers shared by every page.

const ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ESCAPES[c]);
}

/** Marks a string as already-safe HTML, so the `html` tag will not escape it again. */
export class SafeHtml {
  constructor(value) {
    this.value = value;
  }
  toString() {
    return this.value;
  }
}

function render(value) {
  if (value instanceof SafeHtml) return value.value;
  if (Array.isArray(value)) return value.map(render).join("");
  if (value === null || value === undefined || value === false) return "";
  return escapeHtml(value);
}

/**
 * XSS-safe templates: every ${value} is escaped unless it is itself html`...` output.
 *   mount(grid, html`<h3>${product.name}</h3>${items.map((i) => html`<li>${i}</li>`)}`)
 */
export function html(strings, ...values) {
  let out = "";
  strings.forEach((part, i) => {
    out += part + (i < values.length ? render(values[i]) : "");
  });
  return new SafeHtml(out);
}

export function mount(element, safeHtml) {
  element.innerHTML = String(safeHtml);
}

export const qs = (selector, root = document) => root.querySelector(selector);
export const qsa = (selector, root = document) => [...root.querySelectorAll(selector)];

const inr = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
export const formatINR = (amount) => "₹" + inr.format(Number(amount) || 0);

export function formatDate(value) {
  if (!value) return "";
  return new Date(value).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export function initials(name) {
  return String(name || "?")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0].toUpperCase())
    .join("");
}

export function emptyState(icon, message) {
  return html`<div style="text-align:center;padding:30px 10px;color:#929080">
    <div style="font-size:35px">${icon}</div>
    <p>${message}</p>
  </div>`;
}

/** A full-width table row used as an empty or error message. */
export function emptyRow(columns, message) {
  return html`<tr><td colspan="${columns}" style="text-align:center;padding:28px 10px;color:#929080">${message}</td></tr>`;
}

export function debounce(fn, wait = 250) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

/* ---------- toast ---------- */
// Each panel's stylesheet defines its own `.toast` look; `show` is what the designer panel needs.
let toastTimer;
export function toast(message, type = "info") {
  qs(".toast")?.remove();
  clearTimeout(toastTimer);
  const item = document.createElement("div");
  item.className = `toast show ${type}`;
  item.setAttribute("role", "status");
  item.textContent = message;
  document.body.appendChild(item);
  toastTimer = setTimeout(() => item.remove(), 3200);
}

/* ---------- modal ---------- */
export function openModal(id) {
  qs(`#${id}`)?.classList.add("show");
}

export function closeModal(id) {
  qs(`#${id}`)?.classList.remove("show");
}

// The customer page uses .modal; the dashboards use .panel-modal (or the admin's own .admin-modal).
const MODALS = ".modal, .panel-modal, .admin-modal";

document.addEventListener("click", (event) => {
  const closer = event.target.closest("[data-close-modal]");
  if (closer) closer.closest(MODALS)?.classList.remove("show");
  else if (event.target.matches?.(MODALS)) event.target.classList.remove("show");
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") qsa(".show").filter((m) => m.matches(MODALS)).forEach((m) => m.classList.remove("show"));
});

/* ---------- buttons ---------- */
/** Disables a button and shows a spinner while a request runs. Returns a function that restores it. */
export function setBusy(button, label = "Please wait…") {
  const original = button.innerHTML;
  button.disabled = true;
  button.innerHTML = `<span class="spinner" aria-hidden="true"></span> ${escapeHtml(label)}`;
  return () => {
    button.disabled = false;
    button.innerHTML = original;
  };
}

/* ---------- formatting helpers used by the dashboards ---------- */
export const capitalize = (text) => String(text ?? "").charAt(0).toUpperCase() + String(text ?? "").slice(1);

export const stars = (count) => "★".repeat(count) + "☆".repeat(5 - count);

const CATEGORY_ICONS = {
  sofa: "🛋️", chair: "🪑", table: "🪵", bed: "🛏️", lighting: "💡", decor: "🖼️", dining: "🍽️", wardrobe: "🚪",
};
export const categoryIcon = (category) => CATEGORY_ICONS[String(category).toLowerCase()] || "🛋️";

export function timeAgo(value) {
  const seconds = Math.max(0, (Date.now() - new Date(value).getTime()) / 1000);
  const units = [[86400, "day"], [3600, "hour"], [60, "minute"]];
  for (const [size, name] of units) {
    if (seconds >= size) {
      const n = Math.floor(seconds / size);
      return `${n} ${name}${n > 1 ? "s" : ""} ago`;
    }
  }
  return "Just now";
}

/** The topbar search: hides rows and cards of the visible section that do not match what was typed. */
export function liveSearch(input, sectionSelector) {
  input?.addEventListener("input", () => {
    const needle = input.value.trim().toLowerCase();
    qsa(`${sectionSelector} tbody tr, ${sectionSelector} .product-card, ${sectionSelector} .review-card`).forEach((el) => {
      el.style.display = !needle || el.innerText.toLowerCase().includes(needle) ? "" : "none";
    });
  });
}

/** ₹1,84,000 -> ₹1.84L, like the old dashboards. */
export function compactINR(amount) {
  const n = Number(amount) || 0;
  if (n >= 1e7) return `₹${Number((n / 1e7).toFixed(2))}Cr`;
  if (n >= 1e5) return `₹${Number((n / 1e5).toFixed(2))}L`;
  return formatINR(n);
}

/** 8.7 -> "↑ 8.7%", -3 -> "↓ 3%", null -> "" */
export function growthNote(value, suffix = "") {
  if (value === null || value === undefined) return "";
  return `${value >= 0 ? "↑" : "↓"} ${Math.abs(value)}%${suffix ? " " + suffix : ""}`;
}
