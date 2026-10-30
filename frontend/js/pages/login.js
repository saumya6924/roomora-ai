import { api } from "../core/api.js";
import { clearSession, getToken, homeFor, saveSession } from "../core/session.js";
import { openModal, qs, qsa, setBusy } from "../core/ui.js";

const loginForm = qs("#loginForm");
const signupForm = qs("#signupForm");
const message = qs("#authMessage");

// Public signup is Gmail-only (the backend enforces it too). Login accepts any address.
const GMAIL = /^[^\s@]+@gmail\.com$/i;

const PASSWORD_RULES = {
  length: (p) => p.length >= 8,
  capital: (p) => /[A-Z]/.test(p),
  number: (p) => /[0-9]/.test(p),
  special: (p) => /[^A-Za-z0-9]/.test(p),
};

function say(text, type = "error") {
  message.textContent = text;
  message.className = `auth-message ${text ? type : ""}`;
}

function switchTo(signup) {
  loginForm.classList.toggle("hidden", signup);
  signupForm.classList.toggle("hidden", !signup);
  for (const [tab, active] of [
    [qs("#loginTab"), !signup],
    [qs("#signupTab"), signup],
  ]) {
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
  }
  say("");
}

function finishLogin(data, text) {
  saveSession(data.access_token, data.user);
  say(text, "success");
  window.location.replace(homeFor(data.user.role));
}

qs("#loginTab").addEventListener("click", () => switchTo(false));
qs("#signupTab").addEventListener("click", () => switchTo(true));
qs("#forgotLink").addEventListener("click", () => openModal("forgotModal"));

qs("#signupPassword").addEventListener("input", (event) => {
  for (const el of qsa("[data-rule]")) {
    const ok = PASSWORD_RULES[el.dataset.rule](event.target.value);
    el.classList.toggle("valid", ok);
    el.textContent = (ok ? "✓ " : "✕ ") + el.textContent.slice(2);
  }
});

qs("#signupEmail").addEventListener("input", (event) => {
  const hint = qs("#emailHint");
  const value = event.target.value.trim();
  if (!value) {
    hint.textContent = "";
    hint.className = "form-hint";
  } else if (!GMAIL.test(value)) {
    hint.textContent = "Please use an address ending in @gmail.com.";
    hint.className = "form-hint error";
  } else {
    hint.textContent = "✓ Valid email";
    hint.className = "form-hint ok";
  }
});

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const email = qs("#loginEmail").value.trim().toLowerCase();
  const password = qs("#loginPassword").value;
  if (!email || !password) return say("Please enter your email and password.");

  const done = setBusy(qs("#loginButton"), "Logging in…");
  try {
    const data = await api("/auth/login", { method: "POST", body: { email, password }, auth: false });
    finishLogin(data, "Login successful. Opening your dashboard…");
  } catch (error) {
    say(error.message);
    done();
  }
});

signupForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = qs("#signupName").value.trim();
  const email = qs("#signupEmail").value.trim().toLowerCase();
  const mobile = qs("#signupMobile").value.trim();
  const password = qs("#signupPassword").value;

  if (!name || !mobile) return say("Please fill in all required fields.");
  if (!GMAIL.test(email)) return say("Please use an email ending in @gmail.com.");
  if (!Object.values(PASSWORD_RULES).every((rule) => rule(password))) {
    return say("Password needs 8+ characters, one capital letter, one number and one special character.");
  }
  if (password !== qs("#confirmPassword").value) return say("Passwords do not match.");

  const done = setBusy(qs("#signupButton"), "Creating account…");
  try {
    const data = await api("/auth/signup", { method: "POST", body: { name, email, mobile, password }, auth: false });
    finishLogin(data, "Account created. Opening your dashboard…");
  } catch (error) {
    say(error.message);
    done();
  }
});

// Already logged in? Skip the form.
if (getToken()) {
  api("/auth/me")
    .then((me) => window.location.replace(homeFor(me.role)))
    .catch(() => clearSession());
}
