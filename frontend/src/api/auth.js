const TOKEN_KEY = "aapdasetu.accessToken";

export function getAccessToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function storeAccessToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearAccessToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request(path, { method = "GET", body, signal } = {}) {
  const headers = {};
  const token = getAccessToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  let response;
  try {
    response = await fetch(`/api/v1/auth${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error("Unable to reach the account service. Check your connection and try again.", {
      cause: error,
    });
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail;
    const error = new Error(
      typeof detail === "string"
        ? detail
        : detail?.message || `Account request failed (HTTP ${response.status}). Please try again.`,
    );
    error.code = detail?.code;
    error.status = response.status;
    throw error;
  }
  return payload;
}

export function registerAccount(payload) {
  return request("/register", { method: "POST", body: payload });
}

export async function loginAccount(payload) {
  const result = await request("/login", { method: "POST", body: payload });
  storeAccessToken(result.access_token);
  return result.user;
}

export async function logoutAccount() {
  try {
    await request("/logout", { method: "POST" });
  } finally {
    clearAccessToken();
  }
}

export function verifyEmail(token) {
  return request("/verify-email", { method: "POST", body: { token } });
}

export function resendVerification(email) {
  return request("/resend-verification", { method: "POST", body: { email } });
}

export function getCurrentUser(signal) {
  return request("/me", { signal });
}

export function updateCurrentUserProfile(payload) {
  return request("/me", { method: "PATCH", body: payload });
}

export function getAdminUsers(signal) {
  return request("/admin/users", { signal });
}

export function getResponderRequests(signal) {
  return request("/admin/responder-requests", { signal });
}

export function deleteAdminUser(userId) {
  return request(`/admin/users/${encodeURIComponent(userId)}`, { method: "DELETE" });
}

export function updateAdminRole(userId, decision) {
  return request(`/admin/users/${encodeURIComponent(userId)}/role`, {
    method: "POST",
    body: { decision },
  });
}

export function restoreAdminUser(userId) {
  return request(`/admin/users/${encodeURIComponent(userId)}/restore`, { method: "POST" });
}

export function decideResponderRequest(userId, decision) {
  return request(`/admin/responder-requests/${encodeURIComponent(userId)}/decision`, {
    method: "POST",
    body: { decision },
  });
}

export function requestResponderRole() {
  return request("/responder/request", { method: "POST" });
}
