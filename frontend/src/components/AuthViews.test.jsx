import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AdminUsers, AuthView } from "./AuthViews.jsx";

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

describe("account access", () => {
  it("shows a clear error for invalid credentials", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ detail: "Username/email or password is incorrect." }, 401),
    );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<AuthView onAuthenticated={vi.fn()} />);
    await user.type(screen.getByLabelText("Email address or username"), "incorrect-user");
    await user.type(screen.getByLabelText("Password"), "incorrect-password");
    await user.click(screen.getAllByRole("button", { name: "Sign in", exact: true }).at(-1));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Username/email or password is incorrect.");
  });

  describe("administrator access controls", () => {
    it("shows simulation controls only to Super Administrators", async () => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse([])));
      const { rerender } = render(<AdminUsers currentUser={{ id: "admin", is_admin: true }} />);

      expect(screen.queryByRole("button", { name: "Super Admin" })).toBeNull();

      rerender(<AdminUsers currentUser={{ id: "super-admin", is_admin: true, is_super_admin: true }} />);
      await userEvent.click(await screen.findByRole("button", { name: "Super Admin" }));

      expect(screen.getByText("SIMULATION ONLY")).toBeTruthy();
      expect(screen.getByRole("button", { name: "Start simulation" })).toBeTruthy();
    });
  });

  it.each([
    [
      "server errors",
      () => Promise.resolve(jsonResponse({ detail: "Account service is temporarily unavailable." }, 500)),
      "Account service is temporarily unavailable.",
    ],
    [
      "network failures",
      () => Promise.reject(new TypeError("Failed to fetch")),
      "Unable to reach the account service. Check your connection and try again.",
    ],
  ])("surfaces %s to the user", async (_caseName, fetchRequest, expectedMessage) => {
    vi.stubGlobal("fetch", vi.fn(fetchRequest));
    const user = userEvent.setup();

    render(<AuthView onAuthenticated={vi.fn()} />);
    await user.type(screen.getByLabelText("Email address or username"), "manual-user");
    await user.type(screen.getByLabelText("Password"), "password");
    await user.click(screen.getAllByRole("button", { name: "Sign in", exact: true }).at(-1));

    expect((await screen.findByRole("alert")).textContent).toContain(expectedMessage);
  });

  it("toggles password visibility for sign-in and account creation", async () => {
    const user = userEvent.setup();
    render(<AuthView onAuthenticated={vi.fn()} />);

    let password = screen.getByLabelText(/Password/);
    expect(password.type).toBe("password");
    await user.click(screen.getByRole("button", { name: "Show password" }));
    expect(password.type).toBe("text");
    await user.click(screen.getByRole("button", { name: "Hide password" }));
    expect(password.type).toBe("password");

    await user.click(screen.getByRole("button", { name: "Create account", exact: true }));
    password = screen.getByLabelText(/Password/);
    expect(password.type).toBe("password");
    await user.click(screen.getByRole("button", { name: "Show password" }));
    expect(password.type).toBe("text");
    await user.click(screen.getByRole("button", { name: "Sign in", exact: true }));
    expect(screen.getByLabelText(/Password/).type).toBe("password");
  });
});
