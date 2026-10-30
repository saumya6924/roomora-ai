// Page guards and logout.
import { api } from "./api.js";
import { clearSession, getToken, homeFor, saveUser } from "./session.js";

/**
 * Put at the top of a page's script:  const user = await requireRole("admin");
 * Not logged in -> login page. Logged in with another role -> that role's own home page.
 * The page stays hidden until the check passes, so nothing flashes on screen.
 * The backend still checks the role on every API call; this only makes navigation sensible.
 */
export async function requireRole(roles) {
  const allowed = Array.isArray(roles) ? roles : [roles];
  document.documentElement.style.visibility = "hidden";

  if (!getToken()) {
    window.location.replace("login.html");
    return new Promise(() => {}); // never resolves: the page is leaving
  }

  try {
    const me = await api("/auth/me");
    saveUser(me);
    if (!allowed.includes(me.role)) {
      window.location.replace(homeFor(me.role));
      return new Promise(() => {});
    }
    document.documentElement.style.visibility = "visible";
    return me;
  } catch {
    clearSession();
    window.location.replace("login.html");
    return new Promise(() => {});
  }
}

export function logout() {
  clearSession();
  window.location.replace("login.html");
}
