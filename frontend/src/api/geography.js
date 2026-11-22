async function getJson(path, signal) {
  const response = await fetch(path, { signal });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json();
}

function getArrayJson(path, signal) {
  return getJson(path, signal).then((data) => {
    if (!Array.isArray(data)) {
      throw new Error("The API returned an unexpected response.");
    }
    return data;
  });
}

export function getRegions(signal) {
  return getArrayJson("/api/regions", signal);
}

export function getShelters(regionId, signal) {
  const query = regionId ? `?region_id=${encodeURIComponent(regionId)}` : "";
  return getArrayJson(`/api/shelters${query}`, signal);
}

export function getDatasetImports(signal) {
  return getArrayJson("/api/datasets", signal);
}

export function getCoreStatus(signal) {
  return getJson("/api/v1/status", signal);
}

export function getLiveForecasts(refresh = false, signal) {
  return getJson(`/api/v1/forecasts?refresh=${refresh ? "true" : "false"}`, signal);
}

export function getNearestShelters(lat, lon, limit = 5, signal) {
  return getJson(
    `/api/v1/shelters/nearest?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}&limit=${limit}`,
    signal,
  );
}

export function getSosRequests(signal, unassignedOnly = false) {
  const query = unassignedOnly ? "?unassigned_only=true" : "";
  return getJson(`/api/v1/sos${query}`, signal);
}

export function searchPlaces(query, limit = 5, signal) {
  return getJson(
    `/api/v1/geocode?q=${encodeURIComponent(query)}&limit=${limit}`,
    signal,
  );
}

export function reverseGeocode(lat, lon, signal) {
  const query = new URLSearchParams({
    lat: String(lat),
    lon: String(lon),
  });
  return getJson(`/api/v1/geocode/reverse?${query}`, signal);
}

export function getLocalReadiness(lat, lon, signal) {
  return getJson(
    `/api/v1/local-readiness?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`,
    signal,
  );
}
