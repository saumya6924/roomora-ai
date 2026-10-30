// The one implementation of the admin / seller / designer shell: section switching, sidebar, logout.
import { logout } from "./auth.js";
import { initials, qs, qsa } from "./ui.js";

// The three stylesheets name the same parts differently; these are the two vocabularies.
export const SELLER_STYLE = { nav: ".nav-item", section: ".section", sectionActive: "active", sidebarOpen: "open" };
export const ADMIN_STYLE = {
  nav: ".sidebar-link",
  section: ".admin-section",
  sectionActive: "active-section",
  sidebarOpen: "sidebar-open",
};

/**
 * Markup contract:
 *   nav buttons      <button class="nav-item" data-section="orders">
 *   sections         <section id="orders" class="section">
 *   anything else    may carry data-section="orders" too (e.g. a "View all" link)
 *   <button data-action="open-sidebar|close-sidebar|logout">
 *   [data-user-name] [data-user-initials] [data-user-role] are filled from the logged-in user
 */
export function initDashboard(user, { style = SELLER_STYLE, onShow } = {}) {
  const sections = qsa(style.section);
  const known = new Set(sections.map((s) => s.id));

  function show(id) {
    if (!known.has(id)) return;
    sections.forEach((s) => s.classList.toggle(style.sectionActive, s.id === id));
    qsa(`${style.nav}[data-section]`).forEach((n) => n.classList.toggle("active", n.dataset.section === id));
    history.replaceState(null, "", `#${id}`);
    closeSidebar();
    window.scrollTo({ top: 0 });
    onShow?.(id);
  }

  function openSidebar() {
    qs("#sidebar")?.classList.add(style.sidebarOpen);
    qs("#sidebarOverlay")?.classList.add("show");
  }

  function closeSidebar() {
    qs("#sidebar")?.classList.remove(style.sidebarOpen);
    qs("#sidebarOverlay")?.classList.remove("show");
  }

  document.addEventListener("click", (event) => {
    const target = event.target.closest("[data-section], [data-action]");
    if (!target) return;
    if (target.dataset.section) show(target.dataset.section);
    else if (target.dataset.action === "open-sidebar") openSidebar();
    else if (target.dataset.action === "close-sidebar") closeSidebar();
    else if (target.dataset.action === "logout" && confirm("Are you sure you want to logout?")) logout();
  });

  qsa("[data-user-name]").forEach((el) => (el.textContent = user.name));
  qsa("[data-user-initials]").forEach((el) => (el.textContent = initials(user.name)));
  qsa("[data-user-role]").forEach((el) => (el.textContent = user.role));

  const fromHash = location.hash.slice(1);
  const first = qs(`${style.nav}[data-section]`)?.dataset.section;
  show(known.has(fromHash) ? fromHash : first);

  return { show };
}
