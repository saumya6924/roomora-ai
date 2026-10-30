// One place that talks to the backend: adds the login token and turns failures into readable errors.
import { clearSession, getToken } from "./session.js";

export const API = window.ROOMORA_CONFIG.apiBase;

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function messageFrom(data, status) {
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail) && data.detail[0]?.msg) {
    return data.detail[0].msg.replace(/^Value error, /, "");
  }
  return `Something went wrong (error ${status})`;
}

/**
 * api("/products")
 * api("/orders", { method: "POST", body: {...} })
 * api("/uploads/image", { method: "POST", form: formData })
 * `auth: false` skips the token (login and signup).
 */
export async function api(path, { method = "GET", body, form, auth = true, signal } = {}) {
  const headers = {};
  const token = getToken();
  if (auth && token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response;
  try {
    response = await fetch(API + path, {
      method,
      headers,
      body: form ?? (body !== undefined ? JSON.stringify(body) : undefined),
      signal,
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError("Cannot reach the server. Check your connection and try again.", 0);
  }

  let data = {};
  try {
    data = await response.json();
  } catch {
    /* some replies have no body */
  }

  if (!response.ok) {
    // An expired or rejected login: forget it and go back to the login page.
    if (response.status === 401 && auth && token) {
      clearSession();
      window.location.replace("login.html");
    }
    throw new ApiError(messageFrom(data, response.status), response.status);
  }
  return data;
}
