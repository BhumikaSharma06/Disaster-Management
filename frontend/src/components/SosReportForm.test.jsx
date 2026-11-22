import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  createSosRequest: vi.fn(),
  getIncidents: vi.fn(),
}));

vi.mock("../api/eoc.js", () => ({
  createSosRequest: api.createSosRequest,
  getIncidents: api.getIncidents,
}));

import SosReportForm from "./SosReportForm.jsx";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  Reflect.deleteProperty(navigator, "geolocation");
});

describe("SOS report form", () => {
  it("requires a user-requested location and sends an incident-linked, idempotent report", async () => {
    const user = userEvent.setup();
    api.getIncidents.mockResolvedValue([{
      id: 12,
      title: "Test incident",
      hazard_type: "cyclone",
      area_name: "Coastal area",
      status: "active",
    }]);
    api.createSosRequest.mockResolvedValue({ id: 34 });
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: {
        getCurrentPosition: vi.fn((success) => success({
          coords: { latitude: 19.1, longitude: 72.8 },
        })),
      },
    });

    render(<SosReportForm />);
    await user.type(screen.getByLabelText("Type of help needed"), "Medical assistance");
    await user.type(screen.getByLabelText("Details"), "Urgent help needed at the marked location.");
    await user.type(screen.getByLabelText("People affected (optional)"), "2");
    const submit = screen.getByRole("button", { name: "Submit SOS" });
    await user.click(submit);
    expect(await screen.findByText("Share your location before submitting an SOS report.")).toBeTruthy();
    expect(api.createSosRequest).not.toHaveBeenCalled();

    await user.selectOptions(await screen.findByLabelText("Active incident (optional)"), "12");
    await user.click(screen.getByRole("button", { name: "Share current location" }));
    await user.click(submit);

    await waitFor(() => expect(api.createSosRequest).toHaveBeenCalledOnce());
    const payload = api.createSosRequest.mock.calls[0][0];
    expect(payload).toMatchObject({
      incident_id: 12,
      need_type: "Medical assistance",
      urgency: "urgent",
      people_affected: 2,
      latitude: 19.1,
      longitude: 72.8,
    });
    expect(payload.client_submission_id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
    expect((await screen.findByRole("status")).textContent).toContain("SOS report recorded as SOS-34.");
  });
});
