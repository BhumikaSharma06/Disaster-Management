import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App.jsx";

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("authenticated app session", () => {
  it("opens account creation from the signed-out header action", async () => {
    vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    const user = userEvent.setup();

    render(<App />);
    await user.click(await screen.findByRole("button", { name: "Create account", exact: true }));

    expect(await screen.findByRole("heading", { name: "Join the community" })).toBeTruthy();
  });

  it("opens the admin view after login and clears role state on logout", async () => {
    const adminUser = {
      id: "admin-id",
      full_name: "Bootstrap Admin",
      email: "admin@example.test",
      username: "admin",
      is_admin: true,
      is_responder: false,
      is_email_verified: true,
      responder_request_status: "not_requested",
    };
    const fetchMock = vi.fn(async (input, options = {}) => {
      const path = new URL(input, window.location.origin).pathname;
      if (path === "/api/v1/auth/login") {
        return jsonResponse({ access_token: "test-access-token", user: adminUser });
      }
      if (path === "/api/v1/auth/admin/users" || path === "/api/v1/auth/admin/responder-requests") {
        return jsonResponse([]);
      }
      if (path === "/api/v1/safety-tips/admin" || path === "/api/v1/incidents") {
        return jsonResponse([]);
      }
      if (path === "/api/v1/auth/logout" && options.method === "POST") {
        return new Response(null, { status: 204 });
      }
      return jsonResponse({ detail: "Not found" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    const user = userEvent.setup();

    render(<App />);
    await user.click(await screen.findByRole("button", { name: "Sign in", exact: true }));
    await user.type(screen.getByLabelText("Email address or username"), "ADMIN");
    await user.type(screen.getByLabelText("Password"), "admin-password");
    await user.click(screen.getAllByRole("button", { name: "Sign in", exact: true }).at(-1));

    expect(await screen.findByText("Bootstrap Admin")).toBeTruthy();
    expect(await screen.findByRole("heading", { name: "Responder approval requests" })).toBeTruthy();
    expect(screen.getAllByRole("button", { name: "Admin accounts" })).toHaveLength(2);
    expect(localStorage.getItem("aapdasetu.accessToken")).toBe("test-access-token");

    await user.click(screen.getByRole("button", { name: "Log out" }));

    await waitFor(() => {
      expect(localStorage.getItem("aapdasetu.accessToken")).toBeNull();
      expect(screen.queryByRole("button", { name: "Admin accounts" })).toBeNull();
    });
    expect(screen.getByRole("button", { name: "Sign in", exact: true })).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/logout",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("routes help and responder views to the persisted coordination API", async () => {
    const responderUser = {
      id: "responder-id",
      full_name: "Approved Responder",
      email: "responder@example.test",
      is_admin: false,
      is_responder: true,
      is_email_verified: true,
      responder_request_status: "approved",
      contact_phone: "+911234567890",
      home_state: "Example State",
      home_district: "Example District",
      home_locality: "Example Ward",
      home_landmark: "Community centre",
    };
    localStorage.setItem("aapdasetu.accessToken", "responder-access-token");
    const fetchMock = vi.fn(async (input) => {
      const path = new URL(input, window.location.origin).pathname;
      if (path === "/api/v1/auth/me") return jsonResponse(responderUser);
      if (path === "/api/v1/coordination/inbox-count") return jsonResponse({ count: 2 });
      if (path === "/api/v1/help-requests/open-items") return jsonResponse([]);
      if (path === "/api/v1/supply-offers") return jsonResponse([]);
      return jsonResponse({ detail: "Not found" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    const user = userEvent.setup();

    render(<App />);
    expect(await screen.findByText("Approved Responder")).toBeTruthy();

    await user.click(
      within(screen.getByRole("navigation", { name: "Main navigation" }))
        .getByRole("button", { name: "My profile" }),
    );
    expect(await screen.findByLabelText("Contact phone")).toHaveProperty("value", "+911234567890");
    expect(screen.getByLabelText("State").value).toBe("Example State");

    await user.click(
      within(screen.getByRole("navigation", { name: "Main navigation" }))
        .getByRole("button", { name: "Get or offer help" }),
    );
    expect(await screen.findByText("Coordinated relief dispatch")).toBeTruthy();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/help-requests/open-items",
        expect.objectContaining({ method: "GET" }),
      );
    });

    await user.click(
      within(screen.getByRole("navigation", { name: "Main navigation" }))
        .getByRole("button", { name: /Responder inbox/ }),
    );
    expect(await screen.findByText("Active responder queue")).toBeTruthy();
    expect(await screen.findByText("Responder inbox (2)")).toBeTruthy();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/supply-offers",
        expect.objectContaining({ method: "GET" }),
      );
    });
    expect(screen.getAllByLabelText("Responder inbox (2)").length).toBeGreaterThanOrEqual(2);
  });

  it("does not show responder navigation or load the inbox for a community user", async () => {
    const communityUser = {
      id: "community-id",
      full_name: "Community Member",
      email: "community@example.test",
      is_admin: false,
      is_responder: false,
      is_email_verified: true,
      responder_request_status: "not_requested",
    };
    localStorage.setItem("aapdasetu.accessToken", "community-access-token");
    const fetchMock = vi.fn(async (input) => {
      const path = new URL(input, window.location.origin).pathname;
      if (path === "/api/v1/auth/me") return jsonResponse(communityUser);
      if (path === "/api/v1/coordination/inbox-count") return jsonResponse({ count: 0 });
      return jsonResponse({ detail: "Not found" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "scrollTo").mockImplementation(() => {});

    render(<App />);
    expect(await screen.findByText("Community Member")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Responder inbox/ })).toBeNull();
    expect(fetchMock).not.toHaveBeenCalledWith(
      "/api/v1/coordination/inbox-count",
      expect.anything(),
    );
    expect(fetchMock).not.toHaveBeenCalledWith(
      "/api/v1/supply-offers",
      expect.anything(),
    );
    expect(fetchMock).not.toHaveBeenCalledWith(
      expect.stringMatching(/^\/api\/v1\/help-requests\?/),
      expect.anything(),
    );
  });

  it("clears inbox data and hides responder navigation after access is revoked", async () => {
    const responderUser = {
      id: "responder-id",
      full_name: "Approved Responder",
      email: "responder@example.test",
      is_admin: false,
      is_responder: true,
      is_email_verified: true,
      responder_request_status: "approved",
    };
    const communityUser = { ...responderUser, is_responder: false, responder_request_status: "rejected" };
    let accessRevoked = false;
    localStorage.setItem("aapdasetu.accessToken", "responder-access-token");
    const fetchMock = vi.fn(async (input) => {
      const url = new URL(input, window.location.origin);
      if (url.pathname === "/api/v1/auth/me") {
        return jsonResponse(accessRevoked ? communityUser : responderUser);
      }
      if (url.pathname === "/api/v1/coordination/inbox-count") return jsonResponse({ count: 1 });
      if (url.pathname === "/api/v1/help-requests") {
        if (accessRevoked) return jsonResponse({ detail: "Responder access is required." }, 403);
        return jsonResponse([{
          id: 41,
          urgency: "urgent",
          status: "open",
          created_at: "2026-11-22T00:00:00Z",
          contact_name: "Private Requester",
          contact_phone: "+911234567890",
          latitude: 26.1,
          longitude: 86.4,
          items: [{
            id: 8,
            item_name: "Drinking Water",
            units_required: 5,
            units_fulfilled: 0,
            units_remaining: 5,
            unit_label: "packets",
          }],
        }]);
      }
      if (url.pathname === "/api/v1/supply-offers") {
        return jsonResponse(accessRevoked ? { detail: "Responder access is required." } : []);
      }
      return jsonResponse({ detail: "Not found" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    const user = userEvent.setup();

    render(<App />);
    expect(await screen.findByText("Approved Responder")).toBeTruthy();
    await user.click(
      within(screen.getByRole("navigation", { name: "Main navigation" }))
        .getByRole("button", { name: /Responder inbox/ }),
    );
    expect(await screen.findByText("Private Requester")).toBeTruthy();

    accessRevoked = true;
    await user.click(screen.getByRole("button", { name: "Refresh" }));

    expect(await screen.findByText("Responder role required")).toBeTruthy();
    expect(screen.queryByText("Private Requester")).toBeNull();
    expect(screen.queryByRole("button", { name: /Responder inbox/ })).toBeNull();
  });
});
