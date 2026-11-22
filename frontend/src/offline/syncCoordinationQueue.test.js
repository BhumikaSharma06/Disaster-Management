import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const coordinationApi = vi.hoisted(() => ({
  createHelpRequest: vi.fn(),
  createSupplyOffer: vi.fn(),
}));
const queueApi = vi.hoisted(() => ({
  getQueuedCoordinationSubmissions: vi.fn(),
  markCoordinationSubmissionNeedsAttention: vi.fn(),
  removeQueuedCoordinationSubmission: vi.fn(),
}));
const geographyApi = vi.hoisted(() => ({ searchPlaces: vi.fn() }));

vi.mock("../api/coordination.js", () => coordinationApi);
vi.mock("./coordinationQueue.js", () => queueApi);
vi.mock("../api/geography.js", () => geographyApi);

import { syncCoordinationQueue } from "./syncCoordinationQueue.js";

const submission = {
  client_submission_id: "offline-offer-id",
  type: "offer",
  payload: { client_submission_id: "offline-offer-id", units_offered: 4 },
  status: "pending",
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal("navigator", { onLine: true });
  queueApi.getQueuedCoordinationSubmissions.mockResolvedValue([submission]);
  queueApi.markCoordinationSubmissionNeedsAttention.mockResolvedValue(undefined);
  queueApi.removeQueuedCoordinationSubmission.mockResolvedValue(undefined);
  coordinationApi.createSupplyOffer.mockRejectedValue(
    Object.assign(new Error("Only 2 units remain for this request."), { status: 409 }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("offline coordination synchronization", () => {
  it("parks a 409 conflict for user action instead of retrying it", async () => {
    const result = await syncCoordinationQueue();

    expect(coordinationApi.createSupplyOffer).toHaveBeenCalledOnce();
    expect(queueApi.markCoordinationSubmissionNeedsAttention).toHaveBeenCalledWith(
      submission.client_submission_id,
      "Only 2 units remain for this request.",
    );
    expect(queueApi.removeQueuedCoordinationSubmission).not.toHaveBeenCalled();
    expect(result).toMatchObject({
      queued: 1,
      needsAttention: [{ status: "needs_attention" }],
      error: null,
    });
  });

  it("does not automatically retry submissions already marked for attention", async () => {
    queueApi.getQueuedCoordinationSubmissions.mockResolvedValue([
      { ...submission, status: "needs_attention", error_reason: "Conflict" },
    ]);

    const result = await syncCoordinationQueue();

    expect(coordinationApi.createSupplyOffer).not.toHaveBeenCalled();
    expect(result.needsAttention).toHaveLength(1);
    expect(result.error).toBeNull();
  });
});
