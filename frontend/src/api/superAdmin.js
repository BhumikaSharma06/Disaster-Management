import { getAccessToken } from "./auth.js";

async function request(path, { method = "GET", body, signal } = {}) {
  const headers = {};
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response;
  try {
    response = await fetch(`/api/v1/super-admin${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error("Unable to reach the Super Admin service. Check your connection and try again.", {
      cause: error,
    });
  }

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(
      typeof payload.detail === "string"
        ? payload.detail
        : `Super Admin request failed (HTTP ${response.status}). Please try again.`,
    );
    error.status = response.status;
    throw error;
  }
  return payload;
}

export function getSuperAdminSimulations(signal) {
  return request("/simulations", { signal });
}

export function startSuperAdminSimulation(payload) {
  return request("/simulations", { method: "POST", body: payload });
}

export function stopSuperAdminSimulation(simulationId) {
  return request(`/simulations/${encodeURIComponent(simulationId)}/stop`, { method: "POST" });
}

export function getAdminAuditLogs(signal) {
  return request("/audit-logs", { signal });
}
