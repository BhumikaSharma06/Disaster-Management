import { createHelpRequest, createSupplyOffer } from "../api/coordination.js";
import { searchPlaces } from "../api/geography.js";
import {
  getQueuedCoordinationSubmissions,
  markCoordinationSubmissionNeedsAttention,
  removeQueuedCoordinationSubmission,
} from "./coordinationQueue.js";

let activeSync = null;

export async function geocodeHelpRequestPayload(payload) {
  if (Number.isFinite(payload.latitude) && Number.isFinite(payload.longitude)) return payload;
  const query = [payload.landmark, payload.locality, payload.district, payload.state]
    .filter(Boolean)
    .join(", ");
  const result = await searchPlaces(query, 1);
  const place = result.results?.[0];
  if (!place || !Number.isFinite(Number(place.latitude)) || !Number.isFinite(Number(place.longitude))) {
    throw new Error("No matching coordinates were found for this location.");
  }
  return { ...payload, latitude: Number(place.latitude), longitude: Number(place.longitude) };
}

export function syncCoordinationQueue() {
  if (activeSync) return activeSync;
  if (!navigator.onLine) {
    return Promise.resolve({ synced: 0, queued: 0, error: null });
  }

  activeSync = (async () => {
    const queued = await getQueuedCoordinationSubmissions();
    const pending = queued.filter((submission) => submission.status !== "needs_attention");
    let synced = 0;
    const needsAttention = queued.filter((submission) => submission.status === "needs_attention");
    for (const submission of pending) {
      try {
        const payload = submission.type === "request"
          ? await geocodeHelpRequestPayload(submission.payload)
          : submission.payload;
        if (submission.type === "request") await createHelpRequest(payload);
        else await createSupplyOffer(payload);
        await removeQueuedCoordinationSubmission(submission.client_submission_id);
        synced += 1;
      } catch (error) {
        if (
          error.status >= 400 &&
          error.status < 500 &&
          ![408, 425, 429].includes(error.status)
        ) {
          await markCoordinationSubmissionNeedsAttention(
            submission.client_submission_id,
            error.message || `The server rejected this submission (HTTP ${error.status}).`,
          );
          needsAttention.push({ ...submission, status: "needs_attention", error_reason: error.message });
          continue;
        }
        return {
          synced,
          queued: queued.length - synced,
          needsAttention,
          error,
        };
      }
    }
    return { synced, queued: needsAttention.length, needsAttention, error: null };
  })().finally(() => {
    activeSync = null;
  });
  return activeSync;
}
