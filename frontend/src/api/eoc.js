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
    throw new Error("Unable to reach live incident operations. Check the connection and retry.", {
      cause: error,
    });
  }

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(
      typeof payload.detail === "string"
        ? payload.detail
        : `Incident operation failed (HTTP ${response.status}).`,
    );
    error.status = response.status;
    throw error;
  }
  return payload;
}

export async function getIncidents(signal) {
  const records = await request("/incidents", { signal });
  if (!Array.isArray(records)) {
    throw new Error("The incident API returned an unexpected response.");
  }
  return records;
}

export function getIncidentOperations(incidentId, signal) {
  return request(`/incidents/${encodeURIComponent(incidentId)}/operations`, { signal });
}

export function createIncident(payload) {
  return request("/incidents", { method: "POST", body: payload });
}

export function createSosRequest(payload) {
  return request("/sos", { method: "POST", body: payload });
}

export function updateIncidentStatus(incidentId, status) {
  return request(`/incidents/${encodeURIComponent(incidentId)}`, {
    method: "PATCH",
    body: { status },
  });
}

export function updateIncidentShelter(incidentId, shelterId, payload) {
  return request(
    `/incidents/${encodeURIComponent(incidentId)}/shelters/${encodeURIComponent(shelterId)}`,
    { method: "PUT", body: payload },
  );
}

export function updateIncidentSos(incidentId, sosId, status) {
  return request(
    `/incidents/${encodeURIComponent(incidentId)}/sos/${encodeURIComponent(sosId)}`,
    { method: "PATCH", body: { status } },
  );
}
