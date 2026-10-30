// The bell icon in every panel's topbar: unread dot plus a list of the user's notifications.
import { api } from "./api.js";
import { emptyState, html, mount, openModal, qs, timeAgo, toast } from "./ui.js";

const ICONS = { order: "📦", booking: "📅", review: "⭐", product: "🛋️", stock: "⚠️", payout: "💰", system: "🔔" };

function ensureModal() {
  if (qs("#noticeModal")) return;
  const modal = document.createElement("div");
  modal.id = "noticeModal";
  modal.className = "panel-modal";
  modal.innerHTML = `
    <div class="panel-modal-content">
      <div class="panel-modal-header"><h2>Notifications</h2><button data-close-modal aria-label="Close">✕</button></div>
      <div id="noticeList"></div>
      <button class="primary-button" id="noticeReadAll" style="margin-top:14px;width:100%">Mark all as read</button>
    </div>`;
  document.body.appendChild(modal);
  qs("#noticeReadAll").addEventListener("click", async () => {
    await api("/notifications/read-all", { method: "POST" });
    await refresh();
    toast("All notifications marked as read.");
  });
}

async function refresh() {
  const data = await api("/notifications");
  document.querySelectorAll(".notification-dot, .red-dot").forEach((dot) => (dot.style.display = data.unread ? "" : "none"));
  document.querySelectorAll("[data-notification-count]").forEach((el) => (el.textContent = data.unread || ""));
  return data;
}

async function open() {
  ensureModal();
  const data = await refresh();
  mount(
    qs("#noticeList"),
    data.items.length
      ? html`${data.items.map(
          (n) => html`<div class="notice-item ${n.is_read ? "" : "unread"}">
            <span class="notice-icon">${ICONS[n.type] || "🔔"}</span>
            <div><strong>${n.title}</strong><p>${n.body}</p><small>${timeAgo(n.created_at)}</small></div>
          </div>`,
        )}`
      : emptyState("🔔", "You have no notifications yet."),
  );
  openModal("noticeModal");
}

export async function initNotifications() {
  document.addEventListener("click", (event) => {
    if (event.target.closest('[data-action="notifications"]')) open().catch((e) => toast(e.message, "error"));
  });
  await refresh().catch(() => {});
  return { refresh, open };
}
