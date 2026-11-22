import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import ProfileSettings from "./ProfileSettings.jsx";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("profile settings", () => {
  it("saves optional contact and home-address fields and returns the updated account", async () => {
    const profile = {
      id: "community-id",
      full_name: "Community Member",
      email: "community@example.test",
      contact_phone: null,
      home_state: null,
      home_district: null,
      home_locality: null,
      home_landmark: null,
    };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      ...profile,
      contact_phone: "+911234567890",
      home_state: "Example State",
      home_district: "Example District",
      home_locality: "Example Ward",
      home_landmark: null,
    }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);
    const onProfileUpdated = vi.fn();
    const user = userEvent.setup();

    render(<ProfileSettings currentUser={profile} onProfileUpdated={onProfileUpdated} />);
    await user.type(screen.getByLabelText("Contact phone"), "+911234567890");
    await user.type(screen.getByLabelText("State"), "Example State");
    await user.type(screen.getByLabelText("District"), "Example District");
    await user.type(screen.getByLabelText("Village / ward / locality"), "Example Ward");
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    await waitFor(() => expect(onProfileUpdated).toHaveBeenCalledOnce());
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/me",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({
          contact_phone: "+911234567890",
          home_state: "Example State",
          home_district: "Example District",
          home_locality: "Example Ward",
          home_landmark: null,
        }),
      }),
    );
    expect(onProfileUpdated.mock.calls[0][0].home_locality).toBe("Example Ward");
    expect(await screen.findByRole("status")).toHaveProperty(
      "textContent",
      "Profile details saved. They will be used to prefill help and supply forms.",
    );
  });
});
