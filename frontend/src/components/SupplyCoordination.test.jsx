import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ResponderInbox, Response } from "./SupplyCoordination.jsx";

const coordinationApi = vi.hoisted(() => ({
  createHelpRequest: vi.fn(),
  createSupplyOffer: vi.fn(),
  getHelpRequests: vi.fn(),
  getMyHelpRequests: vi.fn(),
  getMySupplyOffers: vi.fn(),
  cancelHelpRequest: vi.fn(),
  getOpenRequestItems: vi.fn(),
  getSupplyOffers: vi.fn(),
  claimSupplyOffer: vi.fn(),
  cancelSupplyOffer: vi.fn(),
  updateSupplyOfferStatus: vi.fn(),
}));
const queueApi = vi.hoisted(() => ({
  getQueuedCoordinationSubmissions: vi.fn(),
  queueCoordinationSubmission: vi.fn(),
  removeQueuedCoordinationSubmission: vi.fn(),
  updateQueuedCoordinationSubmission: vi.fn(),
}));
const geographyApi = vi.hoisted(() => ({
  searchPlaces: vi.fn(),
  reverseGeocode: vi.fn(),
}));

vi.mock("../api/coordination.js", () => coordinationApi);
vi.mock("../offline/coordinationQueue.js", () => queueApi);
vi.mock("../api/geography.js", () => geographyApi);

const openItem = {
  id: 8,
  item_name: "Blanket",
  units_required: 5,
  units_fulfilled: 0,
  units_remaining: 5,
  unit_label: "units",
  help_request_id: 3,
  urgency: "high",
  state: "Example State",
  district: "Example District",
  locality: "Example Ward",
  landmark: null,
  latitude: 26.1,
  longitude: 86.4,
};

const initialOffer = {
  id: 12,
  help_request_item_id: 8,
  item_name: "Blanket",
  units_offered: 2,
  unit_label: "units",
  donor_name: "Donor",
  donor_phone: "+919876543210",
  pickup_location: "Collection point",
  pickup_latitude: null,
  pickup_longitude: null,
  requester_name: "Requester",
  requester_phone: "+911234567890",
  drop_location: "Example Ward, Example District, Example State",
  status: "pending_responder",
  created_at: "2026-11-22T00:00:00Z",
  assignment_responder_id: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  queueApi.getQueuedCoordinationSubmissions.mockResolvedValue([]);
  queueApi.queueCoordinationSubmission.mockResolvedValue(undefined);
  queueApi.updateQueuedCoordinationSubmission.mockResolvedValue(undefined);
  coordinationApi.getOpenRequestItems.mockResolvedValue([openItem]);
  coordinationApi.getHelpRequests.mockResolvedValue([]);
  coordinationApi.getSupplyOffers.mockResolvedValue([]);
  coordinationApi.getMyHelpRequests.mockResolvedValue([]);
  coordinationApi.getMySupplyOffers.mockResolvedValue([]);
  coordinationApi.createHelpRequest.mockResolvedValue({});
  coordinationApi.createSupplyOffer.mockResolvedValue({});
  geographyApi.searchPlaces.mockResolvedValue({
    results: [{
      name: "Example Ward",
      display_name: "Example Ward, Example District",
      latitude: 26.1,
      longitude: 86.4,
      place_id: "example-ward",
    }],
  });
  geographyApi.reverseGeocode.mockResolvedValue({
    available: true,
    state: "Example State",
    district: "Example District",
    locality: "Example Ward",
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("community support coordination", () => {
  it("prefills account contact details and saved address without choosing current coordinates", () => {
    render(
      <Response
        currentUser={{
          full_name: "Profile User",
          contact_phone: "+911234567890",
          home_state: "Saved State",
          home_district: "Saved District",
          home_locality: "Saved Locality",
          home_landmark: "Saved Landmark",
        }}
      />,
    );

    expect(screen.getByLabelText("Contact name").value).toBe("Profile User");
    expect(screen.getByLabelText("Contact phone").value).toBe("+911234567890");
    expect(screen.getByLabelText("State").value).toBe("Saved State");
    expect(screen.getByLabelText("District").value).toBe("Saved District");
    expect(screen.getByLabelText("Village / ward").value).toBe("Saved Locality");
    expect(screen.getByLabelText("Nearby landmark (optional)").value).toBe("Saved Landmark");
    expect(screen.getByText("Choose the incident location before submitting. Your saved address is prefilled but does not confirm your current location.")).toBeTruthy();
  });

  async function selectCurrentLocation(user, onLine = true) {
    const getCurrentPosition = vi.fn((onSuccess) => onSuccess({
      coords: { latitude: 26.1, longitude: 86.4 },
    }));
    vi.stubGlobal("navigator", { ...navigator, onLine, geolocation: { getCurrentPosition } });
    await user.click(screen.getByRole("button", { name: "Use current location" }));
    await waitFor(() => {
      expect(screen.getByLabelText("State").value).toBe("Example State");
      expect(screen.getByLabelText("District").value).toBe("Example District");
      expect(screen.getByLabelText("Village / ward").value).toBe("Example Ward");
    });
  }

  it("submits a geocoded, quantity-bearing help request", async () => {
    const user = userEvent.setup();
    render(<Response />);

    await user.selectOptions(screen.getByLabelText("Need category or item"), "Drinking Water");
    await selectCurrentLocation(user);
    await user.type(screen.getByLabelText("Contact name"), "Requester");
    await user.type(screen.getByLabelText("Contact phone"), "+911234567890");
    await user.click(screen.getByRole("button", { name: "Submit help request" }));

    await waitFor(() => expect(coordinationApi.createHelpRequest).toHaveBeenCalledOnce());
    const [payload] = coordinationApi.createHelpRequest.mock.calls[0];
    expect(payload).toMatchObject({
      item_name: "Drinking Water",
      urgency: "general",
      units_required: 1,
      unit_label: "units",
      state: "Example State",
      district: "Example District",
      locality: "Example Ward",
      contact_name: "Requester",
      latitude: 26.1,
      longitude: 86.4,
    });
    expect(await screen.findByText(
      "Request recorded and routed to the responder queue.",
    )).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Open responder inbox" })).toBeNull();
  });

  it("shows a direct responder-inbox link after successful submission only when authorized", async () => {
    const user = userEvent.setup();
    const onOpenInbox = vi.fn();
    render(<Response canOpenInbox onOpenInbox={onOpenInbox} />);

    await user.selectOptions(screen.getByLabelText("Need category or item"), "Drinking Water");
    await selectCurrentLocation(user);
    await user.type(screen.getByLabelText("Contact name"), "Requester");
    await user.type(screen.getByLabelText("Contact phone"), "+911234567890");
    await user.click(screen.getByRole("button", { name: "Submit help request" }));

    await user.click(await screen.findByRole("link", { name: "Open responder inbox" }));
    expect(onOpenInbox).toHaveBeenCalledOnce();
  });

  it("fills state, district, and village or ward after selecting current location", async () => {
    const user = userEvent.setup();
    render(<Response />);

    await selectCurrentLocation(user);

    await waitFor(() => expect(screen.getByLabelText("Village / ward").value).toBe("Example Ward"));
    expect(screen.getByLabelText("State").readOnly).toBe(false);
    expect(screen.getByLabelText("District").readOnly).toBe(false);
    expect(screen.getByLabelText("Village / ward").readOnly).toBe(false);
    expect(geographyApi.reverseGeocode).toHaveBeenCalledWith(26.1, 86.4);
  });

  it("allows submission with coordinates when administrative address lookup fails", async () => {
    geographyApi.reverseGeocode.mockResolvedValue({
      available: false,
      message: "No address found.",
    });
    const user = userEvent.setup();
    const getCurrentPosition = vi.fn((onSuccess) => onSuccess({
      coords: { latitude: 26.1, longitude: 86.4 },
    }));
    vi.stubGlobal("navigator", { ...navigator, onLine: true, geolocation: { getCurrentPosition } });
    render(<Response />);

    await user.click(screen.getByRole("button", { name: "Use current location" }));

    expect(await screen.findByText("No address found.")).toBeTruthy();
    expect(screen.getByLabelText("State").value).toBe("");
    expect(screen.getByText("Location selected")).toBeTruthy();
    expect(screen.getByLabelText("State").required).toBe(false);
    await user.selectOptions(screen.getByLabelText("Need category or item"), "Drinking Water");
    await user.type(screen.getByLabelText("Contact name"), "Requester");
    await user.type(screen.getByLabelText("Contact phone"), "+911234567890");
    await user.click(screen.getByRole("button", { name: "Submit help request" }));

    await waitFor(() => expect(coordinationApi.createHelpRequest).toHaveBeenCalledOnce());
    expect(coordinationApi.createHelpRequest.mock.calls[0][0]).toMatchObject({
      state: null,
      district: null,
      locality: null,
      latitude: 26.1,
      longitude: 86.4,
    });
  });

  it("limits a supply offer to the selected item's remaining quantity", async () => {
    const user = userEvent.setup();
    render(<Response />);
    await user.click(screen.getByRole("tab", { name: "I can help" }));
    await user.selectOptions(screen.getByLabelText("Open request item"), "8");
    await user.type(screen.getByLabelText("Quantity offered"), "3");
    await user.type(screen.getByLabelText("Your name"), "Donor");
    await user.type(screen.getByLabelText("Your phone"), "+919876543210");
    await user.type(screen.getByLabelText("Pickup location"), "Collection point");
    await user.click(screen.getByRole("button", { name: "Submit supply offer" }));

    await waitFor(() => expect(coordinationApi.createSupplyOffer).toHaveBeenCalledOnce());
    expect(coordinationApi.createSupplyOffer.mock.calls[0][0]).toMatchObject({
      help_request_item_id: 8,
      units_offered: 3,
      donor_name: "Donor",
      donor_phone: "+919876543210",
      pickup_location: "Collection point",
    });
  });

  it("saves submissions in IndexedDB when the browser is offline", async () => {
    vi.stubGlobal("navigator", { ...navigator, onLine: false });
    const user = userEvent.setup();
    render(<Response />);

    await user.selectOptions(screen.getByLabelText("Need category or item"), "Blanket");
    await selectCurrentLocation(user, false);
    await user.type(screen.getByLabelText("Contact name"), "Requester");
    await user.type(screen.getByLabelText("Contact phone"), "+911234567890");
    await user.click(screen.getByRole("button", { name: "Submit help request" }));

    await waitFor(() => expect(queueApi.queueCoordinationSubmission).toHaveBeenCalledOnce());
    expect(coordinationApi.createHelpRequest).not.toHaveBeenCalled();
    expect(await screen.findByText(
      "Saved on this device and will sync when a connection is available.",
    )).toBeTruthy();
  });

  it("omits the optional consent checkbox and privacy note", () => {
    const { container } = render(<Response />);

    expect(screen.queryByRole("checkbox")).toBeNull();
    expect(container.querySelector(".privacy-note")).toBeNull();
  });

  it("surfaces and lets the user edit or dismiss a rejected offline offer", async () => {
    const queuedOffer = {
      client_submission_id: "offline-offer",
      type: "offer",
      status: "needs_attention",
      error_reason: "Only 2 units remain for this request.",
      payload: {
        client_submission_id: "offline-offer",
        help_request_item_id: 8,
        units_offered: 4,
      },
    };
    queueApi.getQueuedCoordinationSubmissions.mockResolvedValue([queuedOffer]);
    const user = userEvent.setup();
    render(<Response />);

    expect(await screen.findByText(queuedOffer.error_reason)).toBeTruthy();
    const quantity = screen.getByRole("spinbutton", { name: "Quantity" });
    await user.clear(quantity);
    await user.type(quantity, "2");
    await user.click(screen.getByRole("button", { name: "Update quantity and retry" }));

    await waitFor(() => {
      expect(queueApi.updateQueuedCoordinationSubmission).toHaveBeenCalledWith(
        "offline-offer",
        expect.objectContaining({ units_offered: 2 }),
      );
    });
    await user.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(queueApi.removeQueuedCoordinationSubmission).toHaveBeenCalledWith("offline-offer");
  });

  it("lets a responder claim an offer and advance its status", async () => {
    let status = "pending_responder";
    coordinationApi.getSupplyOffers.mockImplementation(async () => [{
      ...initialOffer,
      status,
      assignment_responder_id: status === "pending_responder" ? null : "responder-1",
    }]);
    coordinationApi.claimSupplyOffer.mockImplementation(async () => {
      status = "responder_assigned";
    });
    coordinationApi.updateSupplyOfferStatus.mockImplementation(async (_id, next) => {
      status = next;
    });
    const user = userEvent.setup();
    render(<ResponderInbox />);

    expect(await screen.findByRole("link", { name: "+911234567890" })).toBeTruthy();
    expect(screen.getByText("Collection point")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Claim offer" }));
    await user.click(await screen.findByRole("button", { name: "Mark contacted" }));
    const pickedUpQuantity = screen.getByRole("spinbutton", {
      name: "Actual quantity picked up 12",
    });
    await user.clear(pickedUpQuantity);
    await user.type(pickedUpQuantity, "1");
    await user.click(await screen.findByRole("button", { name: "Mark picked up" }));
    await user.click(await screen.findByRole("button", { name: "Mark delivered" }));

    expect(coordinationApi.claimSupplyOffer).toHaveBeenCalledWith(12);
    expect(coordinationApi.updateSupplyOfferStatus).toHaveBeenNthCalledWith(1, 12, "contacted");
    expect(coordinationApi.updateSupplyOfferStatus).toHaveBeenNthCalledWith(2, 12, "picked_up", 1);
    expect(coordinationApi.updateSupplyOfferStatus).toHaveBeenNthCalledWith(3, 12, "delivered");
  });

  it("shows account request history and lets its owner cancel an active request", async () => {
    coordinationApi.getMyHelpRequests.mockResolvedValue([{
      id: 21,
      status: "open",
      created_at: "2026-11-22T00:00:00Z",
      state: "Example State",
      district: "Example District",
      locality: "Example Ward",
      items: [{
        item_name: "Drinking Water",
        units_fulfilled: 0,
        units_required: 5,
        unit_label: "packets",
      }],
    }]);
    const user = userEvent.setup();
    render(<Response currentUser={{ id: "community-1" }} />);

    expect(await screen.findByText(/Drinking Water · 0\/5 packets matched/)).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Cancel request" }));

    await waitFor(() => expect(coordinationApi.cancelHelpRequest).toHaveBeenCalledWith(21));
  });

  it("shows account donation history and lets its owner cancel an active offer", async () => {
    coordinationApi.getMySupplyOffers.mockResolvedValue([{
      ...initialOffer,
      id: 34,
      item_name: "Blanket",
      status: "responder_assigned",
      actual_units_picked_up: null,
    }]);
    const user = userEvent.setup();
    render(<Response currentUser={{ id: "community-1" }} />);
    await user.click(screen.getByRole("tab", { name: "I can help" }));

    expect(await screen.findByText("Blanket · 2 units")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Cancel offer" }));

    await waitFor(() => {
      expect(coordinationApi.cancelSupplyOffer).toHaveBeenCalledWith(34, "donor_cancelled");
    });
  });

  it("shows active help requests in the responder inbox", async () => {
    coordinationApi.getHelpRequests.mockResolvedValue([{
      id: 41,
      urgency: "urgent",
      status: "open",
      created_at: "2026-11-22T00:00:00Z",
      contact_name: "Requester",
      contact_phone: "+911234567890",
      latitude: 26.1,
      longitude: 86.4,
      notes: null,
      items: [{
        id: 8,
        item_name: "Drinking Water",
        units_required: 5,
        units_fulfilled: 0,
        units_remaining: 5,
        unit_label: "packets",
      }],
    }]);
    render(<ResponderInbox />);

    const table = await screen.findByRole("table", { name: "Responder coordination queue" });
    expect(await within(table).findByText("Drinking Water")).toBeTruthy();
    expect(within(table).getByRole("link", { name: "+911234567890" })).toBeTruthy();
    expect(within(table).getByText("No donor offer yet")).toBeTruthy();
    expect(within(table).getByText("Waiting for a donor offer")).toBeTruthy();
    expect(within(table).getAllByRole("row")).toHaveLength(2);
    expect(coordinationApi.getHelpRequests).toHaveBeenCalledWith(
      expect.objectContaining({ active_only: true }),
      expect.any(AbortSignal),
    );
  });
});
