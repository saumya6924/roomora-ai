// Keeps the free-tier backend awake on demand.
//
// Render's free plan sleeps a service after 15 minutes without traffic. Pressing the button pings /health
// straight away (waking it), then pings again every INTERVAL for PINGS pings in total, so the server stays up
// for about an hour. The schedule is stored in localStorage, so reloading the page does not lose it.
//
// INTERVAL is 13 minutes, not 14: browsers slow timers in background tabs (to about once a minute), which could
// push a 14-minute ping past Render's 15-minute limit.
import { API } from "../core/api.js";
import { qs } from "../core/ui.js";

const KEY = "roomoraWake";
const MINUTE = 60_000;
const INTERVAL = 13 * MINUTE;
const PINGS = 5; // the wake-up ping plus four keep-alive pings
const SLEEP_AFTER = 15 * MINUTE;
const TIMEOUT = 90_000; // a cold start can take about a minute

const status = qs("#wakeStatus");
const details = qs("#wakeDetails");
const start = qs("#wakeButton");
const stop = qs("#stopButton");

let state = read();
let pinging = false;

function read() {
  try {
    return JSON.parse(localStorage.getItem(KEY));
  } catch {
    return null;
  }
}

function save() {
  if (state) localStorage.setItem(KEY, JSON.stringify(state));
  else localStorage.removeItem(KEY);
}

const clock = (ms) => new Date(ms).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
const countdown = (ms) => {
  const s = Math.max(0, Math.ceil(ms / 1000));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
};

function setStatus(text, kind = "") {
  status.textContent = text;
  status.className = `wake-status ${kind}`;
}

async function ping() {
  if (pinging) return;
  pinging = true;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT);
  try {
    const response = await fetch(`${API}/health`, { cache: "no-store", signal: controller.signal });
    state.lastOk = response.ok;
  } catch {
    state.lastOk = false;
  } finally {
    clearTimeout(timer);
    state.lastAt = Date.now();
    pinging = false;
    save();
  }
}

function render() {
  const now = Date.now();
  if (!state) {
    setStatus("Server status unknown");
    start.style.display = "";
    stop.style.display = "none";
    details.style.display = "none";
    return;
  }
  start.style.display = "none";
  stop.style.display = "";
  details.style.display = "block";

  const finished = state.pinged >= PINGS;
  const lastPing = state.startedAt + (PINGS - 1) * INTERVAL;
  const awakeUntil = lastPing + SLEEP_AFTER;

  if (pinging && state.pinged <= 1) setStatus("Waking the server… this can take up to a minute.", "busy");
  else if (state.lastOk === false) setStatus("The server did not answer. Trying again at the next ping.", "bad");
  else if (state.lastOk) setStatus(now < awakeUntil ? "✓ The server is awake." : "The keep-awake window has ended.", now < awakeUntil ? "ok" : "");
  else setStatus("Waking the server…", "busy");

  const lines = [`Ping ${Math.min(state.pinged, PINGS)} of ${PINGS} sent`];
  if (!finished) lines.push(`Next ping in ${countdown(state.startedAt + state.pinged * INTERVAL - now)}`);
  if (now < awakeUntil) lines.push(`Stays awake until about ${clock(awakeUntil)}`);
  else lines.push("It will go back to sleep after 15 minutes of no use");
  details.innerHTML = lines.map((line) => `<p>${line}</p>`).join("");
}

async function tick() {
  if (!state) return;
  const due = state.startedAt + state.pinged * INTERVAL;
  if (state.pinged < PINGS && Date.now() >= due && !pinging) {
    state.pinged += 1;
    save();
    render();
    await ping();
  }
  render();
}

start.addEventListener("click", () => {
  state = { startedAt: Date.now(), pinged: 0, lastOk: null, lastAt: null };
  save();
  tick();
});

stop.addEventListener("click", () => {
  state = null;
  save();
  render();
});

// Resume a schedule that was running before the page was reloaded (or drop one that is long over).
if (state && Date.now() > state.startedAt + (PINGS - 1) * INTERVAL + SLEEP_AFTER) state = null;
save();
render();
setInterval(tick, 1000);
tick();
