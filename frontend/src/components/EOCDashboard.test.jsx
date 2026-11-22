import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  getCoreStatus: vi.fn(),
  getLiveForecasts: vi.fn(),
  getShelters: vi.fn(),
  getSosRequests: vi.fn(),
  getIncidents: vi.fn(),
  getIncidentOperations: vi.fn(),
  createIncident: vi.fn(),
  updateIncidentShelter: vi.fn(),
  updateIncidentSos: vi.fn(),
  updateIncidentStatus: vi.fn(),
  getCoordinationSummary: vi.fn(),
  moderateHelpRequest: vi.fn(),
}));

vi.mock("../api/geography.js", () => ({
  getCoreStatus: api.getCoreStatus,
  getLiveForecasts: api.getLiveForecasts,
  getShelters: api.getShelters,
  getSosRequests: api.getSosRequests,
}));

vi.mock("../api/coordination.js", () => ({
  getCoordinationSummary: api.getCoordinationSummary,
  moderateHelpRequest: api.moderateHelpRequest,
}));

vi.mock("../api/eoc.js", () => ({
  getIncidents: api.getIncidents,
  getIncidentOperations: api.getIncidentOperations,
  createIncident: api.createIncident,
  updateIncidentShelter: api.updateIncidentShelter,
  updateIncidentSos: api.updateIncidentSos,
  updateIncidentStatus: api.updateIncidentStatus,
}));

import EOCDashboard from "./EOCDashboard.jsx";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function setupDashboard(incidentRecords = []) {
  api.getCoreStatus.mockResolvedValue({
    telemetry: {
      available: false,
      last_update: null,
      sentinel_count: 1,
    },
  });
  api.getLiveForecasts.mockResolvedValue({ available: false, forecasts: [] });
  api.getShelters.mockResolvedValue([
    {
      id: 8,
      name: "Community Shelter",
      capacity: 100,
      current_occupancy: 91,
      region_id: 3,
      verification_status: "unverified",
      source_name: "test catalogue",
      location: { coordinates: [77.2, 28.6] },
    },
  ]);
  api.getSosRequests.mockResolvedValue({
    requests: [
      {
        id: 42,
        need_type: "Medical help",
        description: "Assistance requested",
        urgency: "critical",
        status: "open",
        longitude: 77.21,
        latitude: 28.61,
      },
    ],
  });
  api.getIncidents.mockResolvedValue(incidentRecords);
  api.getIncidentOperations.mockResolvedValue({
    sos: [],
    shelters: [],
    available_shelters: [],
    fetched_at: "2026-11-23T12:00:00Z",
  });
  api.getCoordinationSummary.mockRejectedValue(new Error("Coordination unavailable in test"));

  return render(<EOCDashboard />);
}

describe("EOC dashboard", () => {
  it("shows a real-data attention item and links it to the record inspector", async () => {
    const user = userEvent.setup();
    setupDashboard();

    const attentionRecord = await screen.findByRole("button", {
      name: /Critical SOS record · SOS-42/,
    });
    await user.click(attentionRecord);

    expect(await screen.findByText("Assistance requested")).toBeTruthy();
    expect(screen.getByText(/People affected:/).textContent).toContain("Not provided");
    expect(screen.getByText(/not confirmed as belonging to an active incident/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Auto-Match|Dispatch Now/ })).toBeNull();
  });

  it("filters persisted SOS records and makes the list navigate to the map", async () => {
    const user = userEvent.setup();
    setupDashboard();

    await user.click(await screen.findByRole("button", { name: /SOS Records/ }));
    await waitFor(() => expect(screen.getByText("Persisted SOS records")).toBeTruthy());
    expect(screen.getByText("SOS-42")).toBeTruthy();

    await user.selectOptions(screen.getByRole("combobox", { name: "URGENCY" }), "critical");
    await user.selectOptions(screen.getByRole("combobox", { name: "STATUS" }), "open");
    await user.click(screen.getByRole("button", { name: "Show on map" }));

    expect(await screen.findByText("Assistance requested")).toBeTruthy();
    expect(screen.getByText("Coordinate plot · schematic canvas · not for navigation")).toBeTruthy();
  });

  it("does not claim incident selection, live routes, or an ML hydrograph without connected data", async () => {
    const user = userEvent.setup();
    setupDashboard();

    expect((await screen.findByRole("combobox", { name: "ACTIVE INCIDENT" })).disabled).toBe(true);
    expect(screen.getByText("No incident boundary or rescue-route feed connected")).toBeTruthy();
    expect(screen.queryByText("Safe Evacuation Corridors")).toBeNull();

    await user.click(screen.getByRole("button", { name: "Provider Snapshot" }));
    expect(screen.getByText(/not a discharge hydrograph, official warning/)).toBeTruthy();
    expect(screen.queryByText(/XGBoost/)).toBeNull();
  });

  it("switches the operational map and records to the selected incident", async () => {
    const user = userEvent.setup();
    const activeIncidents = [
      {
        id: 1,
        title: "Cyclone response",
        hazard_type: "cyclone",
        area_name: "Coastal area",
        status: "active",
      },
      {
        id: 2,
        title: "Flood response",
        hazard_type: "flood",
        area_name: "River area",
        status: "active",
      },
    ];
    setupDashboard(activeIncidents);
    const incidentSelector = await screen.findByRole("combobox", { name: "ACTIVE INCIDENT" });
    await waitFor(() => expect(incidentSelector.value).toBe("1"));
    expect(api.getIncidentOperations).toHaveBeenCalledWith(1, expect.any(AbortSignal));
    expect(screen.queryByText("Assistance requested")).toBeNull();

    api.getIncidentOperations.mockImplementation((incidentId) => Promise.resolve({
      incident: { id: incidentId },
      sos: incidentId === 2 ? [{
        id: 7,
        need_type: "Evacuation",
        description: "Help requested near the river",
        urgency: "urgent",
        status: "open",
        people_affected: 3,
        longitude: 77.3,
        latitude: 28.7,
        created_at: "2026-11-23T12:00:00Z",
        updated_at: "2026-11-23T12:00:00Z",
      }] : [],
      shelters: [],
      available_shelters: [],
      fetched_at: "2026-11-23T12:00:00Z",
    }));
    await user.selectOptions(incidentSelector, "2");
    expect(await screen.findByText(/Help requested near the river/)).toBeTruthy();
    expect(api.getIncidentOperations).toHaveBeenCalledWith(2, expect.any(AbortSignal));
    expect(screen.getByText("Flood response", { selector: "strong" })).toBeTruthy();
  });
});
