const DATABASE_NAME = "aapdasetu-coordination";
const DATABASE_VERSION = 2;
const STORE_NAME = "pending-submissions";

function openQueue() {
  if (!("indexedDB" in globalThis)) {
    return Promise.reject(new Error("Offline storage is unavailable in this browser."));
  }
  return new Promise((resolve, reject) => {
    const opening = indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
    opening.onupgradeneeded = () => {
      const database = opening.result;
      if (!database.objectStoreNames.contains(STORE_NAME)) {
        database.createObjectStore(STORE_NAME, { keyPath: "client_submission_id" });
      }
    };
    opening.onsuccess = () => resolve(opening.result);
    opening.onerror = () => reject(opening.error || new Error("Could not open offline storage."));
    opening.onblocked = () => reject(new Error("Offline storage is blocked by another page."));
  });
}

async function transact(mode, operation) {
  const database = await openQueue();
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, mode);
    const store = transaction.objectStore(STORE_NAME);
    let result;
    try {
      result = operation(store);
    } catch (error) {
      database.close();
      reject(error);
      return;
    }
    transaction.oncomplete = () => {
      database.close();
      resolve(result?.result);
    };
    transaction.onerror = () => {
      database.close();
      reject(transaction.error || new Error("Offline storage operation failed."));
    };
    transaction.onabort = () => {
      database.close();
      reject(transaction.error || new Error("Offline storage operation was cancelled."));
    };
  });
}

export function queueCoordinationSubmission(type, payload) {
  return transact("readwrite", (store) =>
    store.put({
      client_submission_id: payload.client_submission_id,
      type,
      payload,
      queued_at: new Date().toISOString(),
      status: "pending",
      error_reason: null,
    }),
  );
}

export function getQueuedCoordinationSubmissions() {
  return transact("readonly", (store) => store.getAll());
}

export function removeQueuedCoordinationSubmission(clientSubmissionId) {
  return transact("readwrite", (store) => store.delete(clientSubmissionId));
}

export function updateQueuedCoordinationSubmission(clientSubmissionId, payload) {
  return transact("readwrite", (store) => {
    const submission = store.get(clientSubmissionId);
    submission.onsuccess = () => {
      if (submission.result) {
        store.put({
          ...submission.result,
          payload,
          status: "pending",
          error_reason: null,
        });
      }
    };
    return submission;
  });
}

export function markCoordinationSubmissionNeedsAttention(clientSubmissionId, reason) {
  return transact("readwrite", (store) => {
    const submission = store.get(clientSubmissionId);
    submission.onsuccess = () => {
      if (submission.result) {
        store.put({
          ...submission.result,
          status: "needs_attention",
          error_reason: reason,
        });
      }
    };
    return submission;
  });
}
