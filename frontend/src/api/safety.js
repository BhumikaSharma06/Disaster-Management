import { getAccessToken } from "./auth.js";

async function request(path, { method = "GET", body, signal } = {}) {
  const headers = {};
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let response;
  try {
    response = await fetch(`/api/v1${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body), signal });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error("Unable to reach safety-tip operations.", { cause: error });
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof payload.detail === "string" ? payload.detail : `Safety-tip operation failed (HTTP ${response.status}).`);
  }
  return payload;
}

export function getAdminSafetyTips(signal) {
  return request("/safety-tips/admin", { signal });
}

export function getPublishedSafetyTips(signal, language = "en") {
  return request(`/safety-tips?language=${encodeURIComponent(language)}`, { signal });
}

export function createSafetyTip(payload) {
  return request("/safety-tips/admin", { method: "POST", body: payload });
}

export function updateSafetyTip(tipId, payload) {
  return request(`/safety-tips/admin/${encodeURIComponent(tipId)}`, { method: "PATCH", body: payload });
}

export function archiveSafetyTip(tipId) {
  return request(`/safety-tips/admin/${encodeURIComponent(tipId)}`, { method: "DELETE" });
}
