import { getAccessToken } from "./auth.js";

async function request(path, { method = "GET", body, signal } = {}) {
  const headers = {};
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error("Unable to reach the coordination service. Check your connection and try again.", {
      cause: error,
    });
  }

  const payload = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(
      typeof payload?.detail === "string"
        ? payload.detail
        : `Coordination request failed (HTTP ${response.status}). Please try again.`,
    );
    error.status = response.status;
    throw error;
  }
  return payload;
}

function queryString(filters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") params.set(key, value);
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function createHelpRequest(payload) {
  return request("/help-requests", { method: "POST", body: payload });
}

export function getHelpRequests(filters = {}, signal) {
  return request(`/help-requests${queryString(filters)}`, { signal });
}

export function getMyHelpRequests(signal) {
  return request("/coordination/my-help-requests", { signal });
}

export function cancelHelpRequest(requestId) {
  return request(`/help-requests/${encodeURIComponent(requestId)}/cancel`, {
    method: "POST",
  });
}

export function getOpenRequestItems(filters = {}, signal) {
  return request(`/help-requests/open-items${queryString(filters)}`, { signal });
}

export function createSupplyOffer(payload) {
  return request("/supply-offers", { method: "POST", body: payload });
}

export function cancelSupplyOffer(offerId, reason) {
  return request(`/supply-offers/${encodeURIComponent(offerId)}/cancel`, {
    method: "POST",
    body: { reason },
  });
}

export function moderateHelpRequest(requestId, action, reason) {
  return request(`/help-requests/${encodeURIComponent(requestId)}/moderation`, {
    method: "POST",
    body: { action, reason },
  });
}

export function getSupplyOffers(filters = {}, signal) {
  return request(`/supply-offers${queryString(filters)}`, { signal });
}

export function getMySupplyOffers(signal) {
  return request("/coordination/my-supply-offers", { signal });
}

export function claimSupplyOffer(offerId) {
  return request(`/supply-offers/${encodeURIComponent(offerId)}/assign`, {
    method: "POST",
  });
}

export function updateSupplyOfferStatus(offerId, status, actualUnitsPickedUp) {
  return request(`/supply-offers/${encodeURIComponent(offerId)}/status`, {
    method: "PATCH",
    body: {
      status,
      ...(actualUnitsPickedUp === undefined ? {} : { actual_units_picked_up: actualUnitsPickedUp }),
    },
  });
}

export function getInboxCount(signal) {
  return request("/coordination/inbox-count", { signal });
}

export function getCoordinationSummary(signal) {
  return request("/coordination/summary", { signal });
}
