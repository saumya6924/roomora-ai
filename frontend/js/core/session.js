// Where the login lives in the browser. No dependencies, so any module can import it.

export const TOKEN_KEY = "roomoraToken"; // the floating AI editor reads this key too
export const USER_KEY = "roomoraUser";

// Each role's home page, relative to the site root.
export const ROLE_HOME = {
  user: "user.html",
  admin: "admin.html",
  seller: "seller.html",
  designer: "designer.html",
};

export function homeFor(role) {
  return ROLE_HOME[role] || ROLE_HOME.user;
}

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY));
  } catch {
    return null;
  }
}

export function saveSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function saveUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  for (const key of [TOKEN_KEY, USER_KEY, "roomoraRequirements", "roomoraCart"]) {
    try {
      localStorage.removeItem(key);
    } catch {
      /* storage can be unavailable (private mode); nothing to clear */
    }
  }
}
