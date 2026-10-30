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
  return html`<div class="empty-state"><span class="empty-icon">${icon}</span><p>${message}</p></div>`;
}

export function debounce(fn, wait = 250) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

/* ---------- toast ---------- */
export function toast(message, type = "info") {
  let stack = qs(".toast-stack");
  if (!stack) {
    stack = document.createElement("div");
    stack.className = "toast-stack";
    stack.setAttribute("role", "status");
    stack.setAttribute("aria-live", "polite");
    document.body.appendChild(stack);
  }
  const item = document.createElement("div");
  item.className = `toast ${type}`;
  item.textContent = message;
  stack.appendChild(item);
  setTimeout(() => item.remove(), 3500);
}

/* ---------- modal ---------- */
export function openModal(id) {
  qs(`#${id}`)?.classList.add("show");
}

export function closeModal(id) {
  qs(`#${id}`)?.classList.remove("show");
}

document.addEventListener("click", (event) => {
  const closer = event.target.closest("[data-close-modal]");
  if (closer) closer.closest(".modal")?.classList.remove("show");
  else if (event.target.classList?.contains("modal")) event.target.classList.remove("show");
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") qsa(".modal.show").forEach((m) => m.classList.remove("show"));
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
