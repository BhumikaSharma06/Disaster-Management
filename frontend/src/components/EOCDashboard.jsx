import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import GeographyCatalog from "./GeographyCatalog.jsx";
import { getCoreStatus, getLiveForecasts, getShelters, getSosRequests } from "../api/geography.js";
import { getCoordinationSummary, moderateHelpRequest } from "../api/coordination.js";
import {
  createIncident,
  getIncidentOperations,
  getIncidents,
  updateIncidentShelter,
  updateIncidentSos,
  updateIncidentStatus,
} from "../api/eoc.js";
import "./EOCDashboard.css";

function parseCoordinate(value) {
  if (value === null || value === undefined || value === "") return Number.NaN;
  const coordinate = Number(value);
  return Number.isFinite(coordinate) ? coordinate : Number.NaN;
}

// Multilingual CAP Warning Broadcasts
const CAP_BROADCAST_TEMPLATES = {
  extreme: {
    en: "SAMPLE PREVIEW — This sample is not an official warning or confirmation of a current disaster. Follow verified instructions from local authorities.",
    hi: "केवल नमूना — यह आधिकारिक चेतावनी या वर्तमान आपदा की पुष्टि नहीं है। स्थानीय अधिकारियों के सत्यापित निर्देशों का पालन करें।",
    mai: "केवल नमूना — ई आधिकारिक चेतावनी वा वर्तमान आपदाक पुष्टि नहि अछि। स्थानीय अधिकारीक सत्यापित निर्देश मानू।",
  },
  warning: {
    en: "SAMPLE PREVIEW — Keep essential medicines and emergency contacts ready. This sample is not an active alert; check verified local sources for current guidance.",
    hi: "केवल नमूना — आवश्यक दवाइयाँ और आपातकालीन संपर्क तैयार रखें। यह सक्रिय चेतावनी नहीं है; वर्तमान जानकारी के लिए स्थानीय सत्यापित स्रोत देखें।",
    mai: "केवल नमूना — जरूरी दवा आ आपातकालीन संपर्क तैयार राखू। ई सक्रिय चेतावनी नहि अछि; वर्तमान जानकारी लेल स्थानीय सत्यापित स्रोत देखू।",
  },
};

function getAvailableSpeechVoices(synthesis) {
  const voices = synthesis.getVoices();
  if (voices.length > 0) return Promise.resolve(voices);

  return new Promise((resolve) => {
    let timeoutId;
    const finish = () => {
      window.clearTimeout(timeoutId);
      synthesis.removeEventListener("voiceschanged", handleVoicesChanged);
      resolve(synthesis.getVoices());
    };
    const handleVoicesChanged = () => {
      if (synthesis.getVoices().length > 0) finish();
    };

    synthesis.addEventListener("voiceschanged", handleVoicesChanged);
    timeoutId = window.setTimeout(finish, 1500);
  });
}

export default function EOCDashboard({
  language = "en",
  onCoordinationUpdated,
  canModerate = false,
  canManageIncidents = false,
}) {
  const [activeTab, setActiveTab] = useState("map");
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState("");
  const [availableShelters, setAvailableShelters] = useState([]);
  const [selectedCatalogShelterId, setSelectedCatalogShelterId] = useState("");
  const [sosList, setSosList] = useState([]);
  const [sheltersList, setSheltersList] = useState([]);
  const [backendStatus, setBackendStatus] = useState(null);
  const [liveForecasts, setLiveForecasts] = useState([]);
  const [forecastAvailable, setForecastAvailable] = useState(false);
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [dashboardError, setDashboardError] = useState("");
  const [dashboardFetchedAt, setDashboardFetchedAt] = useState(null);
  const [liveOperationsFetchedAt, setLiveOperationsFetchedAt] = useState(null);
  const [operationError, setOperationError] = useState("");
  const [incidentFormOpen, setIncidentFormOpen] = useState(false);
  const [incidentFormError, setIncidentFormError] = useState("");
  const [incidentForm, setIncidentForm] = useState({
    title: "",
    hazard_type: "flood",
    area_name: "",
    description: "",
  });
  const [shelterUpdates, setShelterUpdates] = useState({});
  const [recordActionError, setRecordActionError] = useState("");
  const [sosSeverityFilter, setSosSeverityFilter] = useState("all");
  const [sosStatusFilter, setSosStatusFilter] = useState("all");
  const [shelterOccupancyFilter, setShelterOccupancyFilter] = useState("all");
  const dashboardControllerRef = useRef(null);
  const [coordinationSummary, setCoordinationSummary] = useState(null);
  const [coordinationLoading, setCoordinationLoading] = useState(true);
  const [coordinationError, setCoordinationError] = useState("");
  const [layerFilters, setLayerFilters] = useState({
    shelters: true,
    stations: true,
    sos: true,
  });

  // CAP broadcast form
  const [broadcastSeverity, setBroadcastSeverity] = useState("extreme");
  const [broadcastPrepared, setBroadcastPrepared] = useState(false);
  const [speakingLanguage, setSpeakingLanguage] = useState(null);
  const [speechNotice, setSpeechNotice] = useState("");
  const speechUtteranceRef = useRef(null);
  const speechRequestRef = useRef(0);

  const loadDashboard = useCallback(async (
    refresh = false,
    requestedIncidentId = selectedIncidentId,
    showLoading = true,
  ) => {
    dashboardControllerRef.current?.abort();
    const controller = new AbortController();
    dashboardControllerRef.current = controller;
    if (showLoading) setDashboardLoading(true);
    setDashboardError("");
    try {
      const [status, forecasts, shelterRecords, incidentRecords] = await Promise.all([
        getCoreStatus(controller.signal),
        getLiveForecasts(refresh, controller.signal),
        getShelters(null, controller.signal),
        getIncidents(controller.signal),
      ]);

      const activeIncidents = incidentRecords.filter((incident) => incident.status !== "closed");
      const selectedIncident = activeIncidents.find(
        (incident) => String(incident.id) === String(requestedIncidentId),
      ) || activeIncidents[0] || null;
      const nextIncidentId = selectedIncident ? String(selectedIncident.id) : "";
      if (nextIncidentId !== selectedIncidentId) setSelectedIncidentId(nextIncidentId);
      setIncidents(incidentRecords);

      const [sosData, incidentOperations] = await Promise.all([
        selectedIncident
          ? Promise.resolve(null)
          : getSosRequests(controller.signal, true),
        selectedIncident
          ? getIncidentOperations(selectedIncident.id, controller.signal)
          : Promise.resolve(null),
      ]);
      setBackendStatus(status);
      setForecastAvailable(forecasts.available);
      setLiveForecasts(forecasts.available ? forecasts.forecasts : []);
      setOperationError("");
      setLiveOperationsFetchedAt(
        incidentOperations?.fetched_at || null,
      );
      const sosRecords = incidentOperations?.sos ?? sosData?.requests ?? [];
      setSosList(
        sosRecords.map((request) => ({
          id: `SOS-${request.id}`,
          sosId: request.id,
          district: selectedIncident?.area_name || "Area not provided",
          village: request.description || request.need_type,
          need: request.need_type,
          severity: request.urgency === "urgent" ? "critical" : request.urgency,
          people: request.people_affected ?? null,
          details: request.description || "No additional details supplied.",
          time: request.created_at
            ? new Date(request.created_at).toLocaleString()
            : null,
          updatedAt: request.updated_at || null,
          status: request.status,
          lon: parseCoordinate(request.longitude),
          lat: parseCoordinate(request.latitude),
          matchedResponder: null,
        })),
      );
      const shelterData = incidentOperations?.shelters || shelterRecords.map((shelter) => ({
        id: shelter.id,
        name: shelter.name,
        capacity: shelter.capacity,
        current_occupancy: shelter.current_occupancy,
        source_name: shelter.source_name,
        verification_status: shelter.verification_status,
        region_id: shelter.region_id,
        location: shelter.location,
      }));
      setAvailableShelters(incidentOperations?.available_shelters || []);
      setSheltersList(shelterData.map((shelter) => {
        const lon = parseCoordinate(
          shelter.longitude ?? shelter.location?.coordinates?.[0],
        );
        const lat = parseCoordinate(
          shelter.latitude ?? shelter.location?.coordinates?.[1],
        );
        const capacity = Number(shelter.capacity ?? 0);
        const hasOccupancy = shelter.current_occupancy !== null
          && shelter.current_occupancy !== undefined;
        const occupied = hasOccupancy ? Number(shelter.current_occupancy) : null;
        return {
          id: `db-${shelter.id}`,
          shelterId: shelter.id,
          name: shelter.name,
          district: selectedIncident?.area_name
            || (shelter.region_id ? `Region ${shelter.region_id}` : "Area not provided"),
          capacity,
          occupied,
          lon,
          lat,
          verificationStatus: shelter.verification_status,
          sourceName: shelter.source_name,
          operationalStatus: shelter.operational_status || null,
          updateNote: shelter.update_note || "",
          updatedAt: shelter.updated_at || null,
          status: shelter.operational_status
            || (capacity > 0 && occupied !== null && occupied / capacity >= 0.85
              ? "near_full"
              : "recorded"),
        };
      }).filter((shelter) => Number.isFinite(shelter.lon) && Number.isFinite(shelter.lat)));
      setDashboardFetchedAt(new Date().toISOString());
    } catch (error) {
      if (error.name !== "AbortError") {
        setDashboardError(error.message || "Could not load dashboard records.");
        if (requestedIncidentId) setOperationError(error.message || "Could not load incident operations.");
      }
    } finally {
      if (!controller.signal.aborted && showLoading) setDashboardLoading(false);
    }
  }, [selectedIncidentId]);

  useEffect(() => {
    loadDashboard(false);
    return () => dashboardControllerRef.current?.abort();
  }, [loadDashboard]);

  useEffect(() => {
    const intervalId = window.setInterval(
      () => loadDashboard(false, selectedIncidentId, false),
      15000,
    );
    return () => window.clearInterval(intervalId);
  }, [loadDashboard, selectedIncidentId]);

  async function submitIncident(event) {
    event.preventDefault();
    setIncidentFormError("");
    try {
      const incident = await createIncident(incidentForm);
      setIncidentForm({
        title: "",
        hazard_type: "flood",
        area_name: "",
        description: "",
      });
      setIncidentFormOpen(false);
      await loadDashboard(false, incident.id);
    } catch (error) {
      setIncidentFormError(error.message || "Could not create the incident.");
    }
  }

  async function saveShelterUpdate(shelter) {
    const values = shelterUpdates[shelter.shelterId] || {};
    const hasOccupancyInput = Object.prototype.hasOwnProperty.call(values, "occupancy");
    setRecordActionError("");
    try {
      await updateIncidentShelter(selectedIncidentId, shelter.shelterId, {
        operational_status: values.status || shelter.operationalStatus || "unknown",
        current_occupancy: hasOccupancyInput
          ? values.occupancy === "" ? null : Number(values.occupancy)
          : shelter.occupied,
        update_note: values.note || null,
      });
      await loadDashboard(false, selectedIncidentId, false);
    } catch (error) {
      setRecordActionError(error.message || "Could not update shelter operations.");
    }
  }

  async function saveSosStatus(sos, status) {
    setRecordActionError("");
    try {
      await updateIncidentSos(selectedIncidentId, sos.sosId, status);
      await loadDashboard(false, selectedIncidentId, false);
    } catch (error) {
      setRecordActionError(error.message || "Could not update the SOS record.");
    }
  }

  async function linkCatalogShelter() {
    if (!selectedIncidentId || !selectedCatalogShelterId) return;
    setRecordActionError("");
    try {
      await updateIncidentShelter(selectedIncidentId, selectedCatalogShelterId, {
        operational_status: "unknown",
        current_occupancy: null,
        update_note: null,
      });
      setSelectedCatalogShelterId("");
      await loadDashboard(false, selectedIncidentId, false);
    } catch (error) {
      setRecordActionError(error.message || "Could not link the shelter to this incident.");
    }
  }

  async function changeIncidentStatus(status) {
    if (!selectedIncidentId) return;
    setRecordActionError("");
    try {
      await updateIncidentStatus(selectedIncidentId, status);
      await loadDashboard(false, status === "closed" ? "" : selectedIncidentId);
    } catch (error) {
      setRecordActionError(error.message || "Could not update incident status.");
    }
  }

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    async function refreshCoordination() {
      if (active) setCoordinationLoading(true);
      try {
        const summary = await getCoordinationSummary(controller.signal);
        if (active) {
          setCoordinationSummary(summary);
          setCoordinationError("");
          onCoordinationUpdated?.();
        }
      } catch (error) {
        if (active && error.name !== "AbortError") {
          setCoordinationError(error.message || "Could not load live coordination records.");
          setCoordinationSummary(null);
        }
      } finally {
        if (active) setCoordinationLoading(false);
      }
    }
    refreshCoordination();
    const intervalId = window.setInterval(refreshCoordination, 30000);
    return () => {
      active = false;
      window.clearInterval(intervalId);
      controller.abort();
    };
  }, [onCoordinationUpdated]);

  useEffect(() => () => {
    speechRequestRef.current += 1;
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  }, []);

  async function speakAlert(text, languageKey) {
    if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) {
      setSpeechNotice("Text-to-speech is not supported in this browser.");
      return;
    }

    const synthesis = window.speechSynthesis;
    const requestId = speechRequestRef.current + 1;
    speechRequestRef.current = requestId;
    const voiceLanguage = languageKey === "en" ? "en" : "hi";
    const preferredLocale = languageKey === "en" ? "en-IN" : "hi-IN";
    synthesis.cancel();
    speechUtteranceRef.current = null;
    setSpeakingLanguage(languageKey);
    setSpeechNotice("Loading an available voice…");

    const voices = await getAvailableSpeechVoices(synthesis);
    if (speechRequestRef.current !== requestId) return;
    const matchingVoices = voices.filter((voice) =>
      voice.lang.toLowerCase().split("-")[0] === voiceLanguage
    );
    const selectedVoice = matchingVoices.sort((a, b) => {
      const aExact = a.lang.toLowerCase() === preferredLocale.toLowerCase() ? 1 : 0;
      const bExact = b.lang.toLowerCase() === preferredLocale.toLowerCase() ? 1 : 0;
      return bExact - aExact || Number(b.localService) - Number(a.localService);
    })[0];

    if (!selectedVoice) {
      setSpeakingLanguage(null);
      setSpeechNotice(
        `No ${languageKey === "en" ? "English" : "Hindi"} voice is available. Install a matching voice in your device's speech settings and try again.`
      );
      return;
    }

    synthesis.cancel();
    const spokenText = text
      .replace(/m³\/s/g, "cubic metres per second")
      .replace(/घनमीटर\/सेकंड/g, "घन मीटर प्रति सेकंड");
    const utterance = new SpeechSynthesisUtterance(spokenText);
    utterance.voice = selectedVoice;
    utterance.lang = selectedVoice.lang || preferredLocale;
    utterance.rate = languageKey === "en" ? 0.92 : 0.82;
    speechUtteranceRef.current = utterance;
    setSpeakingLanguage(languageKey);
    setSpeechNotice(
      languageKey === "mai"
        ? "Playing the Maithili text with a Hindi voice; a Maithili voice may not be available on this device."
        : ""
    );

    const finishSpeaking = () => {
      if (speechUtteranceRef.current !== utterance || speechRequestRef.current !== requestId) return;
      speechUtteranceRef.current = null;
      setSpeakingLanguage(null);
    };
    utterance.onend = finishSpeaking;
    utterance.onerror = (event) => {
      finishSpeaking();
      if (event.error !== "canceled" && event.error !== "interrupted") {
        setSpeechNotice("Speech playback failed. Check your device's speech settings and try again.");
      }
    };

    try {
      synthesis.speak(utterance);
    } catch {
      finishSpeaking();
      setSpeechNotice("Speech playback could not start. Check your device's speech settings and try again.");
    }
  }

  async function moderateRequest(request, action, reason) {
    setCoordinationError("");
    try {
      await moderateHelpRequest(request.id, action, reason);
      setCoordinationSummary(await getCoordinationSummary());
      onCoordinationUpdated?.();
    } catch (error) {
      setCoordinationError(error.message || "Could not update the help request.");
    }
  }

  function handleSpeechButton(text, languageKey) {
    if (speakingLanguage === languageKey) {
      window.speechSynthesis.cancel();
      speechRequestRef.current += 1;
      speechUtteranceRef.current = null;
      setSpeakingLanguage(null);
      setSpeechNotice("Playback stopped.");
      return;
    }
    speakAlert(text, languageKey);
  }

  // Keep unreported incident occupancy distinct from a measured zero.
  const stats = useMemo(() => {
    const totalShelterCapacity = sheltersList.reduce((acc, s) => acc + s.capacity, 0);
    const allOccupancyKnown = sheltersList.length > 0
      && sheltersList.every((shelter) => shelter.capacity > 0 && shelter.occupied !== null);
    const totalOccupied = sheltersList.reduce(
      (acc, shelter) => acc + (shelter.occupied ?? 0),
      0,
    );
    const pendingSos = sosList.filter((s) => ["pending", "open"].includes(s.status)).length;
    const reportsWithPeopleCount = sosList.filter((s) => s.people !== null).length;
    const peopleAffected = sosList.reduce((total, request) => total + (request.people || 0), 0);
    const criticalSos = sosList.filter((s) =>
      ["critical", "urgent"].includes(s.severity) && ["pending", "open"].includes(s.status),
    );
    const highOccupancyShelters = sheltersList.filter(
      (shelter) =>
        shelter.capacity > 0
        && shelter.occupied !== null
        && shelter.occupied / shelter.capacity >= 0.85,
    );
    const highestForecast = liveForecasts.reduce(
      (highest, forecast) => (!highest || Number(forecast.score) > Number(highest.score) ? forecast : highest),
      null,
    );

    return {
      totalCapacity: totalShelterCapacity,
      totalOccupied: allOccupancyKnown ? totalOccupied : null,
      occupancyKnownCount: sheltersList.filter((shelter) => shelter.occupied !== null).length,
      occupancyPct: totalShelterCapacity && allOccupancyKnown
        ? Math.round((totalOccupied / totalShelterCapacity) * 100)
        : null,
      pendingSos,
      peopleAffected: reportsWithPeopleCount ? peopleAffected : null,
      sosRecordsWithoutPeopleCount: sosList.length - reportsWithPeopleCount,
      criticalSos,
      highOccupancyShelters,
      liveForecastCount: liveForecasts.length,
      highestForecast,
    };
  }, [sheltersList, sosList, liveForecasts]);

  const mapBounds = useMemo(() => {
    const points = [
      ...(selectedIncidentId ? [] : liveForecasts),
      ...sheltersList,
      ...sosList,
    ].filter((item) => Number.isFinite(parseCoordinate(item.longitude ?? item.lon))
      && Number.isFinite(parseCoordinate(item.latitude ?? item.lat)));
    if (!points.length) return null;
    const longitudes = points.map((point) => parseCoordinate(point.longitude ?? point.lon));
    const latitudes = points.map((point) => parseCoordinate(point.latitude ?? point.lat));
    const longitudeSpan = Math.max(...longitudes) - Math.min(...longitudes);
    const latitudeSpan = Math.max(...latitudes) - Math.min(...latitudes);
    return {
      minLon: Math.min(...longitudes) - Math.max(longitudeSpan * 0.1, 0.01),
      maxLon: Math.max(...longitudes) + Math.max(longitudeSpan * 0.1, 0.01),
      minLat: Math.min(...latitudes) - Math.max(latitudeSpan * 0.1, 0.01),
      maxLat: Math.max(...latitudes) + Math.max(latitudeSpan * 0.1, 0.01),
    };
  }, [liveForecasts, sheltersList, sosList, selectedIncidentId]);

  function project(lon, lat) {
    if (!mapBounds) return { x: 450, y: 300 };
    const x = ((lon - mapBounds.minLon) / (mapBounds.maxLon - mapBounds.minLon)) * 820 + 40;
    const y = 560 - ((lat - mapBounds.minLat) / (mapBounds.maxLat - mapBounds.minLat)) * 510;
    return { x, y };
  }

  const filteredShelters = useMemo(() => {
    if (shelterOccupancyFilter === "all") return sheltersList;
    return sheltersList.filter((shelter) => {
      if (!shelter.capacity || shelter.occupied === null) return false;
      const occupancy = shelter.occupied / shelter.capacity;
      return shelterOccupancyFilter === "high" ? occupancy >= 0.85 : occupancy < 0.85;
    });
  }, [sheltersList, shelterOccupancyFilter]);

  const filteredGauges = useMemo(() => {
    if (selectedIncidentId) return [];
    return liveForecasts.filter((forecast) =>
      Number.isFinite(parseCoordinate(forecast.longitude))
      && Number.isFinite(parseCoordinate(forecast.latitude)),
    ).map((forecast, index) => ({
      id: `provider-${index}`,
      name: `${forecast.region} Sentinel`,
      district: forecast.region || "Pan-India",
      lon: parseCoordinate(forecast.longitude),
      lat: parseCoordinate(forecast.latitude),
      status:
        forecast.level === "red"
          ? "danger"
          : forecast.level === "orange"
            ? "warning"
            : "normal",
      score: forecast.score,
    }));
  }, [liveForecasts, selectedIncidentId]);

  const filteredSos = useMemo(() => {
    return sosList.filter((sos) =>
      (sosSeverityFilter === "all" || sos.severity === sosSeverityFilter)
      && (sosStatusFilter === "all" || sos.status === sosStatusFilter),
    );
  }, [sosList, sosSeverityFilter, sosStatusFilter]);
  const selectedIncident = incidents.find(
    (incident) => String(incident.id) === selectedIncidentId,
  ) || null;

  function openFeature(type, data) {
    setSelectedFeature({ type, data });
    setActiveTab("map");
  }

  function handleMapMarkerKey(event, type, data) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openFeature(type, data);
    }
  }

  return (
    <div className="eoc-root">
      {/* 1. TOP COMMAND BAR */}
      <header className="eoc-command-bar">
        <div className="eoc-brand-cluster">
          <div className="eoc-radar-badge">
            <span className="eoc-radar-pulse" />
            <span className="eoc-radar-icon">EOC</span>
          </div>
          <div>
            <div className="eoc-system-title">
              <strong>{selectedIncident?.title || "Emergency Operations Center"}</strong>
              <span className={`eoc-badge-level ${stats.highestForecast?.level === "red" ? "eoc-badge-critical" : stats.highestForecast?.level === "orange" ? "eoc-badge-warning" : "eoc-badge-normal"}`}>
                {selectedIncident
                  ? selectedIncident.status.toUpperCase()
                  : stats.highestForecast
                  ? `${stats.highestForecast.level?.toUpperCase() || "MONITORED"} RISK`
                  : dashboardLoading
                    ? "LOADING LIVE DATA"
                    : "AWAITING PROVIDER"}
              </span>
            </div>
            <p className="eoc-jurisdiction">
              {selectedIncident
                ? `${selectedIncident.hazard_type} · ${selectedIncident.area_name}`
                : "Incident-linked records are not selected"}
            </p>
          </div>
        </div>

        <div className="eoc-bar-controls">
          <div className="eoc-control-group">
            <label className="eoc-label-small" htmlFor="eoc-incident-select">ACTIVE INCIDENT</label>
            <select
              id="eoc-incident-select"
              value={selectedIncidentId}
              disabled={!incidents.some((incident) => incident.status !== "closed")}
              className="eoc-select"
              onChange={(event) => {
                setSelectedIncidentId(event.target.value);
                loadDashboard(false, event.target.value);
              }}
            >
              {incidents.filter((incident) => incident.status !== "closed").length === 0
                ? <option value="">No active incidents</option>
                : incidents.filter((incident) => incident.status !== "closed").map((incident) => (
                  <option key={incident.id} value={String(incident.id)}>
                    {incident.title} · {incident.hazard_type} · {incident.area_name}
                  </option>
                ))}
            </select>
          </div>
          {canManageIncidents && (
            <button
              type="button"
              className="button button-outline eoc-refresh-button"
              onClick={() => setIncidentFormOpen((open) => !open)}
            >
              {incidentFormOpen ? "Cancel" : "Create incident"}
            </button>
          )}
          <button
            type="button"
            className="button button-outline eoc-refresh-button"
            onClick={() => loadDashboard(true)}
            disabled={dashboardLoading}
          >
            {dashboardLoading ? "Refreshing…" : "Refresh data"}
          </button>
          <button
            type="button"
            className="button button-outline eoc-refresh-button"
            onClick={() => window.print()}
          >
            Print brief
          </button>
        </div>
      </header>

      {incidentFormOpen && canManageIncidents && (
        <form className="eoc-incident-form" onSubmit={submitIncident}>
          <label>
            Incident title
            <input
              required
              maxLength={160}
              value={incidentForm.title}
              onChange={(event) => setIncidentForm({ ...incidentForm, title: event.target.value })}
            />
          </label>
          <label>
            Hazard
            <input
              required
              maxLength={40}
              value={incidentForm.hazard_type}
              onChange={(event) => setIncidentForm({ ...incidentForm, hazard_type: event.target.value })}
            />
          </label>
          <label>
            Affected area
            <input
              required
              maxLength={200}
              value={incidentForm.area_name}
              onChange={(event) => setIncidentForm({ ...incidentForm, area_name: event.target.value })}
            />
          </label>
          <label>
            Operator notes
            <input
              maxLength={4000}
              value={incidentForm.description}
              onChange={(event) => setIncidentForm({ ...incidentForm, description: event.target.value })}
            />
          </label>
          <button type="submit" className="button button-primary">Open incident</button>
          {incidentFormError && <p role="alert">{incidentFormError}</p>}
        </form>
      )}

      {(dashboardLoading || dashboardError || backendStatus) && (
        <div className={`eoc-data-banner ${dashboardError ? "eoc-data-error" : ""}`}>
          <span className="eoc-data-dot" />
          <span>
            {dashboardLoading
              ? "Loading provider snapshot and database records…"
              : dashboardError
                ? dashboardError
                : forecastAvailable
                  ? `Provider snapshot available · ${stats.liveForecastCount} provider risk indicators`
                  : "Provider snapshot unavailable · official warning feed is not connected"}
          </span>
          <small>
            Dashboard fetched {dashboardFetchedAt ? new Date(dashboardFetchedAt).toLocaleString() : "not yet"}
            {selectedIncidentId
              ? ` · Incident operations refresh every 15 seconds${liveOperationsFetchedAt ? ` · Last incident sync ${new Date(liveOperationsFetchedAt).toLocaleTimeString()}` : ""}`
              : ""}
            {backendStatus?.telemetry?.last_update
              ? ` · Provider update ${new Date(backendStatus.telemetry.last_update).toLocaleString()}`
              : " · Provider update time unavailable"}
          </small>
        </div>
      )}
      {operationError && <p className="eoc-action-error" role="alert">{operationError}</p>}
      {recordActionError && <p className="eoc-action-error" role="alert">{recordActionError}</p>}
      {selectedIncidentId && canManageIncidents && (
        <div className="eoc-incident-lifecycle">
          <span>
            Incident status: <strong>
              {incidents.find((incident) => String(incident.id) === selectedIncidentId)?.status}
            </strong>
          </span>
          <select
            aria-label="Update incident status"
            className="eoc-select"
            value={incidents.find((incident) => String(incident.id) === selectedIncidentId)?.status || "active"}
            onChange={(event) => changeIncidentStatus(event.target.value)}
          >
            <option value="active">Active</option>
            <option value="monitoring">Monitoring</option>
            <option value="closed">Closed</option>
          </select>
        </div>
      )}

      <section className="eoc-print-brief" aria-hidden="true">
        <h1>AapdaSetu · EOC data brief</h1>
        <p>Generated {new Date().toLocaleString()} · {selectedIncident ? `${selectedIncident.title} · ${selectedIncident.hazard_type}` : "Unassigned operational records"}</p>
        <p>Verified area boundaries, responder inventory, and rescue routing are not connected.</p>
        <dl>
          <dt>Highest provider risk score</dt>
          <dd>{stats.highestForecast ? `${stats.highestForecast.score} · ${stats.highestForecast.region}` : "Unavailable"}</dd>
          <dt>Open SOS database records</dt>
          <dd>{stats.pendingSos}</dd>
          <dt>Shelter records</dt>
          <dd>{sheltersList.length} · Occupancy {stats.totalOccupied === null
            ? stats.occupancyKnownCount ? "incomplete" : "not reported"
            : `${stats.totalOccupied}/${stats.totalCapacity || "capacity unknown"}`}</dd>
          <dt>Provider snapshot last update</dt>
          <dd>{backendStatus?.telemetry?.last_update ? new Date(backendStatus.telemetry.last_update).toLocaleString() : "Not reported"}</dd>
        </dl>
        <p>Provider indicators and catalogue records are not official warnings or confirmation of current conditions. AapdaSetu is not an emergency service.</p>
      </section>

      <section className="eoc-attention-panel" aria-labelledby="eoc-attention-title">
        <div className="eoc-attention-heading">
          <div>
            <span className="section-kicker">REVIEW QUEUE</span>
            <h2 id="eoc-attention-title">Attention to review</h2>
          </div>
          <span>{selectedIncident
            ? "Selected-incident records · citizen/operator submitted, not externally verified"
            : "Unassigned database records · not a verified live incident queue"}</span>
        </div>
        <div className="eoc-attention-items">
          {stats.criticalSos.map((sos) => (
            <button
              type="button"
              className="eoc-attention-item eoc-attention-critical"
              key={sos.id}
              onClick={() => openFeature("sos", sos)}
            >
              <strong>Critical SOS record · {sos.id}</strong>
              <span>{sos.village} · {sos.need} · Open record</span>
            </button>
          ))}
          {stats.highOccupancyShelters.map((shelter) => (
            <button
              type="button"
              className="eoc-attention-item eoc-attention-warning"
              key={shelter.id}
              onClick={() => openFeature("shelter", shelter)}
            >
              <strong>Shelter occupancy record at or above 85%</strong>
              <span>{shelter.name} · Recorded {shelter.occupied}/{shelter.capacity} · Review freshness</span>
            </button>
          ))}
          {stats.criticalSos.length === 0 && stats.highOccupancyShelters.length === 0 && (
            <div className="eoc-attention-empty">
              No critical SOS or high recorded-occupancy records are available to review.
            </div>
          )}
          {(!backendStatus?.telemetry?.last_update || !sheltersList.length) && (
            <div className="eoc-attention-item eoc-attention-info">
              <strong>Data readiness needs review</strong>
              <span>
                {!backendStatus?.telemetry?.last_update && "No provider update timestamp is available. "}
                {!sheltersList.length && "No shelter records are available."}
              </span>
            </div>
          )}
        </div>
      </section>

      <section className="panel eoc-coordination-panel" aria-label="Cross-area supply coordination">
        <div className="eoc-coordination-heading">
          <div>
            <span className="section-kicker">CROSS-AREA SUPPLY COORDINATION</span>
            <h2>Help requests, offers, and fulfillment</h2>
            <p>These coordination records are not yet associated with a selected incident.</p>
          </div>
          <button
            type="button"
            className="button button-outline"
            onClick={() => getCoordinationSummary().then(setCoordinationSummary).catch((error) => setCoordinationError(error.message))}
          >
            Refresh
          </button>
        </div>
        {coordinationLoading && !coordinationSummary ? (
          <p className="coordination-muted">Loading coordination records…</p>
        ) : coordinationError ? (
          <p className="coordination-error" role="alert">{coordinationError}</p>
        ) : coordinationSummary ? (
          <>
            <div className="eoc-coordination-metrics">
              <article><span>Help requests</span><strong>{coordinationSummary.metrics.help_requests}</strong></article>
              <article><span>Open / partial</span><strong>{coordinationSummary.metrics.open_help_requests + coordinationSummary.metrics.partially_fulfilled_requests}</strong></article>
              <article><span>Supply offers</span><strong>{coordinationSummary.metrics.supply_offers}</strong></article>
              <article><span>Units fulfilled</span><strong>{coordinationSummary.metrics.units_fulfilled} / {coordinationSummary.metrics.units_requested}</strong></article>
              <article><span>Awaiting responders</span><strong>{coordinationSummary.metrics.pending_responder}</strong></article>
              <article><span>Responder assignments</span><strong>{coordinationSummary.metrics.responder_assignments}</strong></article>
              <article><span>Delivered</span><strong>{coordinationSummary.metrics.delivered}</strong></article>
            </div>
            <div className="eoc-coordination-records">
              <div>
                <h3>Recent help requests</h3>
                {coordinationSummary.help_requests.slice(0, 5).map((request) => (
                  <article className="eoc-coordination-record" key={request.id}>
                    <strong>{request.items.map((item) => `${item.item_name}: ${item.units_fulfilled}/${item.units_required} ${item.unit_label}`).join(" · ")}</strong>
                    <span>{request.locality}, {request.district}, {request.state} · {request.status}</span>
                        {request.moderation_reason && (
                          <span>Flagged: {request.moderation_reason}</span>
                        )}
                        {canModerate && request.status !== "closed" && (
                          <div className="eoc-request-moderation">
                            <button type="button" className="button button-outline" onClick={() => moderateRequest(request, "flag", "spam")}>Flag spam</button>
                            <button type="button" className="button button-outline" onClick={() => moderateRequest(request, "flag", "duplicate")}>Flag duplicate</button>
                            <button type="button" className="button button-outline" onClick={() => moderateRequest(request, "close", "spam")}>Close as spam</button>
                            <button type="button" className="button button-outline" onClick={() => moderateRequest(request, "close", "duplicate")}>Close as duplicate</button>
                          </div>
                        )}
                      </article>
                ))}
                {coordinationSummary.help_requests.length === 0 && <p className="coordination-muted">No help requests recorded.</p>}
              </div>
              <div>
                <h3>Recent supply offers</h3>
                {coordinationSummary.supply_offers.slice(0, 5).map((offer) => (
                  <article className="eoc-coordination-record" key={offer.id}>
                    <strong>{offer.item_name} · {offer.units_offered} {offer.unit_label}</strong>
                    <span>{offer.pickup_location} → {offer.drop_location} · {offer.status.replaceAll("_", " ")}</span>
                  </article>
                ))}
                {coordinationSummary.supply_offers.length === 0 && <p className="coordination-muted">No supply offers recorded.</p>}
              </div>
            </div>
          </>
        ) : null}
      </section>

      {/* 2. SITUATION SUMMARY */}
      <section className="eoc-kpi-grid">
        <button
          type="button"
          className={`eoc-kpi-card eoc-kpi-action ${stats.highestForecast?.level === "red" ? "kpi-danger" : stats.highestForecast?.level === "orange" ? "kpi-warning" : "kpi-normal"}`}
          onClick={() => setActiveTab("hydro")}
        >
          <div className="kpi-top">
            <span className="kpi-icon">🌊</span>
            <span className="kpi-tag">
              {stats.highestForecast
                ? selectedIncident
                  ? "FLOOD SNAPSHOT · NOT LINKED"
                  : `${stats.highestForecast.level?.toUpperCase()} PROVIDER RISK`
                : "NO SNAPSHOT"}
            </span>
          </div>
          <div className="kpi-value">{stats.highestForecast ? `${stats.highestForecast.score}` : "—"}</div>
          <div className="kpi-title">
            {selectedIncident ? "Unlinked flood provider indicator" : "Highest provider flood risk score"}
          </div>
          <div className="kpi-sub">
            {stats.highestForecast
              ? `${stats.highestForecast.region} · open-provider indicator${selectedIncident ? " · outside this incident" : ""}`
              : "No initialized provider snapshot"}
          </div>
          <span className="kpi-drilldown">View provider snapshot →</span>
        </button>

        <div className="eoc-kpi-card kpi-neutral">
          <div className="kpi-top">
            <span className="kpi-icon">👥</span>
            <span className="kpi-tag">{stats.peopleAffected === null ? "NO COUNTS REPORTED" : "REPORTED TOTAL"}</span>
          </div>
          <div className="kpi-value">{stats.peopleAffected?.toLocaleString() ?? "—"}</div>
          <div className="kpi-title">People reported in SOS records</div>
          <div className="kpi-sub">
            {stats.peopleAffected === null
              ? "No SOS record includes a people count"
              : `Sum of reported counts; ${stats.sosRecordsWithoutPeopleCount} record(s) have no count and totals may overlap`}
          </div>
        </div>

        <button
          type="button"
          className="eoc-kpi-card eoc-kpi-action kpi-shelter"
          onClick={() => setActiveTab("shelters")}
        >
          <div className="kpi-top">
            <span className="kpi-icon">🏠</span>
            <span className="kpi-tag">{stats.occupancyPct === null ? "NO OCCUPANCY DATA" : `${stats.occupancyPct}% RECORDED`}</span>
          </div>
          <div className="kpi-value">
            {stats.totalCapacity
              ? <>{stats.totalOccupied === null ? "—" : stats.totalOccupied.toLocaleString()} <span className="kpi-unit">/ {stats.totalCapacity.toLocaleString()}</span></>
              : "—"}
          </div>
          <div className="kpi-title">{stats.totalCapacity ? `${sheltersList.length} shelter records` : "Shelter occupancy"}</div>
          <div className="kpi-sub">
            {stats.totalCapacity
              ? stats.totalOccupied === null
                ? stats.occupancyKnownCount
                  ? `Incomplete occupancy · ${stats.occupancyKnownCount} report(s) available`
                  : "No current occupancy has been reported"
                : `${stats.totalCapacity - stats.totalOccupied} remaining recorded capacity · freshness shown per shelter`
              : "No shelter records returned by the database"}
          </div>
          <span className="kpi-drilldown">Review shelter records →</span>
        </button>

        <button
          type="button"
          className="eoc-kpi-card eoc-kpi-action kpi-sos"
          onClick={() => setActiveTab("triage")}
        >
          <div className="kpi-top">
            <span className="kpi-icon">🆘</span>
            <span className="kpi-tag">{stats.pendingSos} OPEN RECORDS</span>
          </div>
          <div className="kpi-value">{stats.pendingSos} <span className="kpi-unit">records</span></div>
          <div className="kpi-title">Open SOS records</div>
          <div className="kpi-sub">
            {selectedIncident ? "SOS records linked to selected incident" : "Persisted records · incident association unavailable"}
          </div>
          <span className="kpi-drilldown">Review SOS records →</span>
        </button>

        <div className="eoc-kpi-card kpi-responder">
          <div className="kpi-top">
            <span className="kpi-icon">🚤</span>
            <span className="kpi-tag">NOT CONNECTED</span>
          </div>
          <div className="kpi-value">—</div>
          <div className="kpi-title">Responder availability</div>
          <div className="kpi-sub">No live responder inventory is connected</div>
        </div>
      </section>

      {/* 3. NAVIGATION TABS FOR EOC */}
      <nav className="eoc-nav-tabs">
        <button
          className={`eoc-tab-btn ${activeTab === "map" ? "active" : ""}`}
          onClick={() => setActiveTab("map")}
        >
          GIS Situation Map
        </button>
        <button
          className={`eoc-tab-btn ${activeTab === "triage" ? "active" : ""}`}
          onClick={() => setActiveTab("triage")}
        >
          SOS Records ({stats.pendingSos})
        </button>
        <button
          className={`eoc-tab-btn ${activeTab === "hydro" ? "active" : ""}`}
          onClick={() => setActiveTab("hydro")}
        >
          Provider Snapshot
        </button>
        <button
          className={`eoc-tab-btn ${activeTab === "shelters" ? "active" : ""}`}
          onClick={() => setActiveTab("shelters")}
        >
          Shelter Records ({sheltersList.length})
        </button>
        <button
          className={`eoc-tab-btn ${activeTab === "catalog" ? "active" : ""}`}
          onClick={() => setActiveTab("catalog")}
        >
          Database Catalog
        </button>
        <button
          className={`eoc-tab-btn ${activeTab === "broadcast" ? "active" : ""}`}
          onClick={() => setActiveTab("broadcast")}
        >
          Multilingual Alert Bulletin
        </button>
      </nav>

      {/* TAB CONTENT 1: GIS SITUATION MAP */}
      {activeTab === "map" && (
        <div className="eoc-map-view">
          <div className="eoc-map-toolbar">
            <div className="eoc-map-layers">
              <span className="toolbar-label">RECORD LAYERS:</span>
              <label>
                <input
                  type="checkbox"
                  checked={layerFilters.shelters}
                  onChange={(e) => setLayerFilters({ ...layerFilters, shelters: e.target.checked })}
                />
                Shelters ({filteredShelters.length})
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={layerFilters.stations}
                  onChange={(e) => setLayerFilters({ ...layerFilters, stations: e.target.checked })}
                />
                Provider points ({filteredGauges.length})
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={layerFilters.sos}
                  onChange={(e) => setLayerFilters({ ...layerFilters, sos: e.target.checked })}
                />
                SOS records ({filteredSos.length})
              </label>
            </div>
            <span className="eoc-map-unavailable">No incident boundary or rescue-route feed connected</span>
          </div>

          <div className="eoc-map-stage">
            <svg
              className="eoc-gis-svg"
              viewBox="0 0 900 600"
              preserveAspectRatio="xMidYMid meet"
              aria-label="Schematic record map; not a navigation map"
            >
              <defs>
                <radialGradient id="sosGlow" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#ff0000" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#ff0000" stopOpacity="0" />
                </radialGradient>
              </defs>

              {/* Map Canvas Background */}
              <rect width="900" height="600" fill="#10252c" rx="8" />

              <text x="22" y="30" fill="#9abac1" fontSize="12">
                Coordinate plot · schematic canvas · not for navigation
              </text>

              {layerFilters.stations &&
                filteredGauges.map((g) => {
                  const { x, y } = project(g.lon, g.lat);
                  return (
                    <g
                      key={g.id}
                      className={`gauge-node ${selectedFeature?.data.id === g.id ? "map-feature-selected" : ""}`}
                      transform={`translate(${x}, ${y})`}
                      onClick={() => openFeature("station", g)}
                      onKeyDown={(event) => handleMapMarkerKey(event, "station", g)}
                      style={{ cursor: "pointer" }}
                      role="button"
                      tabIndex="0"
                      aria-label={`Open provider point ${g.name}`}
                    >
                      <circle r="10" fill="#256b86" fillOpacity="0.5" className="node-halo" />
                      <circle r="6" fill="#48b5cc" stroke="#fff" strokeWidth="2" />
                      <text x="12" y="4" fill="#ffffff" fontSize="11" fontWeight="bold">
                        {g.name}
                      </text>
                      <text x="12" y="16" fill="#a8e6ff" fontSize="10">
                        Provider score: {g.score ?? "—"} · {g.status.toUpperCase()}
                      </text>
                    </g>
                  );
                })}

              {layerFilters.shelters &&
                filteredShelters.filter((item) => Number.isFinite(item.lon) && Number.isFinite(item.lat)).map((s) => {
                  const { x, y } = project(s.lon, s.lat);
                  const occRatio = s.capacity && s.occupied !== null
                    ? s.occupied / s.capacity
                    : null;
                  const markerColor = s.capacity
                    ? occRatio === null ? "#66868a" : occRatio >= 0.85 ? "#cf6259" : occRatio >= 0.65 ? "#c39a45" : "#398b72"
                    : "#66868a";

                  return (
                    <g
                      key={s.id}
                      className={`shelter-node ${selectedFeature?.data.id === s.id ? "map-feature-selected" : ""}`}
                      transform={`translate(${x}, ${y})`}
                      onClick={() => openFeature("shelter", s)}
                      onKeyDown={(event) => handleMapMarkerKey(event, "shelter", s)}
                      style={{ cursor: "pointer" }}
                      role="button"
                      tabIndex="0"
                      aria-label={`Open shelter record ${s.name}`}
                    >
                      <rect x="-8" y="-8" width="16" height="16" rx="3" fill={markerColor} stroke="#fff" strokeWidth="1.5" />
                      <text x="0" y="3" textAnchor="middle" fill="#fff" fontSize="9" fontWeight="bold">
                        H
                      </text>
                      <text x="10" y="-2" fill="#d9f7be" fontSize="10" fontWeight="500">
                        {s.name}
                      </text>
                    </g>
                  );
                })}

              {layerFilters.sos &&
                filteredSos.filter((item) => Number.isFinite(item.lon) && Number.isFinite(item.lat)).map((sos) => {
                  const { x, y } = project(sos.lon, sos.lat);
                  const isCritical = sos.severity === "critical";

                  return (
                    <g
                      key={sos.id}
                      className={`sos-beacon-node ${selectedFeature?.data.id === sos.id ? "map-feature-selected" : ""}`}
                      transform={`translate(${x}, ${y})`}
                      onClick={() => openFeature("sos", sos)}
                      onKeyDown={(event) => handleMapMarkerKey(event, "sos", sos)}
                      style={{ cursor: "pointer" }}
                      role="button"
                      tabIndex="0"
                      aria-label={`Open SOS record ${sos.id}`}
                    >
                      <circle r="18" fill="url(#sosGlow)" className="sos-pulse" />
                      <circle r="8" fill={isCritical ? "#f5222d" : "#fa8c16"} stroke="#fff" strokeWidth="2" />
                      <text x="0" y="3" textAnchor="middle" fill="#fff" fontSize="8" fontWeight="bold">
                        !
                      </text>
                      <text x="12" y="-2" fill="#ffa39e" fontSize="10" fontWeight="bold">
                        {sos.id} ({sos.need})
                      </text>
                    </g>
                  );
                })}
            </svg>

            {/* MAP LEGEND */}
            <div className="eoc-map-legend">
              <span className="legend-title">DISPLAYED RECORDS:</span>
              {!selectedIncidentId && <span><span className="leg-dot leg-danger" /> Provider risk point</span>}
              <span><span className="leg-dot leg-shelter-good" /> {selectedIncidentId ? "Incident shelter" : "Shelter catalogue record"}</span>
              <span><span className="leg-dot leg-sos" /> {selectedIncidentId ? "Incident SOS record" : "Persisted SOS record"}</span>
            </div>
          </div>

          {/* INSPECTION DRAWER FOR SELECTED FEATURE */}
          {selectedFeature && (
            <div className="eoc-inspect-panel">
              <div className="inspect-head">
                <strong>
                  {selectedFeature.type === "shelter" && "🏠 Designated Shelter Details"}
                  {selectedFeature.type === "station" && "📍 Hydrological Gauge Telemetry"}
                  {selectedFeature.type === "sos" && "🚨 Active SOS Distress Ticket"}
                </strong>
                <button className="inspect-close" onClick={() => setSelectedFeature(null)}>✕</button>
              </div>

              {selectedFeature.type === "shelter" && (
                <div className="inspect-body">
                  <h3>{selectedFeature.data.name}</h3>
                  <p>Area: <strong>{selectedFeature.data.district}</strong> · Source: <strong>{selectedFeature.data.sourceName || "Not recorded"}</strong></p>
                  <div className="inspect-stat-row">
                    <div>Recorded capacity: <strong>{selectedFeature.data.capacity || "Not reported"}</strong></div>
                    <div>Occupancy: <strong>{selectedFeature.data.occupied !== null && selectedFeature.data.capacity ? `${selectedFeature.data.occupied} (${Math.round((selectedFeature.data.occupied / selectedFeature.data.capacity) * 100)}%)` : "Not reported"}</strong></div>
                    <div>Verification: <strong>{selectedFeature.data.verificationStatus || "unverified"}</strong></div>
                    <div>Freshness: <strong>Not provided by catalogue</strong></div>
                  </div>
                  {selectedFeature.data.capacity > 0 && selectedFeature.data.occupied !== null && (
                    <div className="inspect-progress-track" aria-label="Recorded occupancy percentage">
                      <div
                        className="inspect-progress-fill"
                        style={{
                          width: `${Math.min(100, (selectedFeature.data.occupied / selectedFeature.data.capacity) * 100)}%`,
                          backgroundColor: (selectedFeature.data.occupied / selectedFeature.data.capacity) > 0.85 ? "#f5222d" : "#52c41a",
                        }}
                      />
                    </div>
                  )}
                  <button type="button" className="button button-outline" onClick={() => setActiveTab("shelters")}>
                    View shelter records
                  </button>
                </div>
              )}

              {selectedFeature.type === "station" && (
                <div className="inspect-body">
                  <h3>{selectedFeature.data.name}</h3>
                  <p>Open-provider indicator. This is not an official observation, warning, or flood forecast.</p>
                  <div className="inspect-stat-row">
                    <div>Risk score: <strong>{selectedFeature.data.score ?? "Not reported"}</strong></div>
                    <div>Provider level: <strong>{selectedFeature.data.status}</strong></div>
                    <div>Region: <strong>{selectedFeature.data.district}</strong></div>
                    <div>Provider update: <strong>{backendStatus?.telemetry?.last_update ? new Date(backendStatus.telemetry.last_update).toLocaleString() : "Not reported"}</strong></div>
                  </div>
                </div>
              )}

              {selectedFeature.type === "sos" && (
                <div className="inspect-body">
                  <div className="inspect-tag-row">
                    <span className="badge-sos-id">{selectedFeature.data.id}</span>
                    <span className={`badge-severity-critical ${selectedFeature.data.severity}`}>{selectedFeature.data.severity || "priority not reported"}</span>
                  </div>
                  <h3>{selectedFeature.data.village} ({selectedFeature.data.district})</h3>
                  <p className="inspect-desc">{selectedFeature.data.details}</p>
                  <p>Reported time: <strong>{selectedFeature.data.time || "Not provided"}</strong> · People affected: <strong>{selectedFeature.data.people ?? "Not provided"}</strong> · Status: <strong>{selectedFeature.data.status}</strong></p>
                  {selectedIncidentId
                    ? <p className="catalog-disclaimer">Linked to the selected incident. Status changes are operator-recorded and do not dispatch a responder.</p>
                    : <p className="catalog-disclaimer">This SOS record is not confirmed as belonging to an active incident. No matching or dispatch action is connected here.</p>}
                  {canModerate && selectedIncidentId && selectedFeature.data.sosId && (
                    <div className="eoc-record-actions">
                      {selectedFeature.data.status === "open" && (
                        <button
                          type="button"
                          className="button button-outline"
                          onClick={() => saveSosStatus(selectedFeature.data, "acknowledged")}
                        >
                          Acknowledge
                        </button>
                      )}
                      {["open", "acknowledged"].includes(selectedFeature.data.status) && (
                        <button
                          type="button"
                          className="button button-outline"
                          onClick={() => saveSosStatus(selectedFeature.data, "resolved")}
                        >
                          Mark resolved
                        </button>
                      )}
                    </div>
                  )}
                  <button type="button" className="button button-outline" onClick={() => setActiveTab("triage")}>
                    View SOS records
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT 2: SOS TRIAGE & RESPONSE MATCHING */}
      {activeTab === "triage" && (
        <div className="eoc-triage-view">
          <div className="triage-header">
            <div>
              <h2>Persisted SOS records</h2>
              <p>{selectedIncident
                ? `SOS records linked to ${selectedIncident.title}; new citizen reports appear on the next 15-second refresh.`
                : "Records shown here have not been associated with an active incident. People counts and timestamps are displayed when provided."}</p>
            </div>
            <label className="eoc-control-group">
              <span className="eoc-label-small">URGENCY</span>
              <select
                className="eoc-select"
                value={sosSeverityFilter}
                onChange={(event) => setSosSeverityFilter(event.target.value)}
              >
                <option value="all">All urgency levels</option>
                {[...new Set(sosList.map((sos) => sos.severity).filter(Boolean))]
                  .sort()
                  .map((severity) => (
                    <option key={severity} value={severity}>{severity}</option>
                  ))}
              </select>
            </label>
            <label className="eoc-control-group">
              <span className="eoc-label-small">STATUS</span>
              <select
                className="eoc-select"
                value={sosStatusFilter}
                onChange={(event) => setSosStatusFilter(event.target.value)}
              >
                <option value="all">All statuses</option>
                {[...new Set(sosList.map((sos) => sos.status).filter(Boolean))]
                  .sort()
                  .map((status) => (
                    <option key={status} value={status}>{status.replaceAll("_", " ")}</option>
                  ))}
              </select>
            </label>
          </div>

          <div className="triage-table-wrapper">
            <table className="triage-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Priority</th>
                  <th>Location</th>
                  <th>Category</th>
                  <th>Victims</th>
                  <th>Situation Details</th>
                  <th>Map</th>
                </tr>
              </thead>
              <tbody>
                {filteredSos.length === 0 ? (
                  <tr><td colSpan="7"><div className="eoc-empty-state"><strong>No SOS records match these filters</strong><span>Change urgency or status, or refresh the dashboard.</span></div></td></tr>
                ) : filteredSos.map((sos) => (
                  <tr
                    key={sos.id}
                    className={sos.severity === "critical" ? "row-critical" : "row-normal"}
                    onClick={() => openFeature("sos", sos)}
                  >
                    <td><code>{sos.id}</code></td>
                    <td>
                      <span className={`pill-score ${sos.severity}`}>
                        {sos.severity || "Not reported"}
                      </span>
                    </td>
                    <td>
                      <strong>{sos.district}</strong>
                      <div className="cell-sub">{sos.village}</div>
                    </td>
                    <td><span className="badge-category">{sos.need}</span></td>
                    <td><strong>{sos.people ?? "Not reported"}</strong></td>
                    <td className="cell-details">{sos.details}</td>
                    <td>
                      <button
                        type="button"
                        className="button button-outline"
                        onClick={(event) => {
                          event.stopPropagation();
                          openFeature("sos", sos);
                        }}
                        disabled={!Number.isFinite(sos.lon) || !Number.isFinite(sos.lat)}
                        title={!Number.isFinite(sos.lon) || !Number.isFinite(sos.lat) ? "No coordinates are available for this record" : "Show this record on the schematic map"}
                      >
                        {Number.isFinite(sos.lon) && Number.isFinite(sos.lat) ? "Show on map" : "No coordinates"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB CONTENT 3: PROVIDER SNAPSHOT */}
      {activeTab === "hydro" && (
        <div className="eoc-hydro-view">
          <div className="hydro-header">
            <div>
              <h2>Flood provider snapshot</h2>
              <p>Provider risk indicators from configured open providers—not a discharge hydrograph, official warning, or trained-model forecast.</p>
            </div>
            <div className="hydro-badges">
              <span className="badge-model">Provider indicator</span>
              <span className="badge-split">Snapshot · not a time series</span>
            </div>
          </div>

          <div className="hydro-chart-panel">
            <svg className="hydro-svg" viewBox="0 0 840 320" aria-label="Provider risk score comparison">
              <text x="34" y="34" fill="#88adb9" fontSize="12">Provider score (0–100)</text>
              {[0, 25, 50, 75, 100].map((score) => {
                const y = 280 - score * 2.3;
                return (
                  <g key={score}>
                    <line x1="70" y1={y} x2="810" y2={y} stroke="#254854" strokeWidth="1" strokeDasharray="3 4" />
                    <text x="28" y={y + 4} fill="#88adb9" fontSize="10">{score}</text>
                  </g>
                );
              })}
              {liveForecasts.filter((forecast) => Number.isFinite(Number(forecast.score))).length > 0
                ? liveForecasts.filter((forecast) => Number.isFinite(Number(forecast.score))).slice(0, 9).map((forecast, idx) => {
                const x = 105 + idx * 78;
                const y = 280 - (Math.max(0, Math.min(100, Number(forecast.score))) * 2.3);
                const color = forecast.level === "red" ? "#cf6259" : forecast.level === "orange" ? "#c39a45" : "#398b72";
                return (
                  <g key={`${forecast.region}-${idx}`}>
                    <circle cx={x} cy={y} r="7" fill={color} stroke="#fff" strokeWidth="1.5" />
                    <text x={x} y={y - 12} textAnchor="middle" fill="#ffffff" fontSize="10" fontWeight="bold">
                      {forecast.score}
                    </text>
                    <text x={x} y="304" textAnchor="middle" fill="#88adb9" fontSize="9">
                      {forecast.region?.slice(0, 12) || "Sentinel"}
                    </text>
                  </g>
                );
              }) : (
                <text x="420" y="160" textAnchor="middle" fill="#88adb9" fontSize="13">
                  Provider snapshot unavailable
                </text>
              )}
            </svg>
          </div>

          <div className="hydro-analysis-cards">
            <div className="analysis-card">
              <h3>Provider indicators</h3>
              <div className="analysis-val text-danger">{stats.liveForecastCount ? `${stats.liveForecastCount} scores` : "Unavailable"}</div>
              <p>{stats.highestForecast ? `${stats.highestForecast.region} has the highest score in this snapshot.` : "No provider snapshot is available."}</p>
            </div>
            <div className="analysis-card">
              <h3>Incident status</h3>
              <div className="analysis-val text-warning">{selectedIncident?.status || "No incident selected"}</div>
              <p>Operator-managed status does not replace an official warning or independently confirm conditions.</p>
            </div>
            <div className="analysis-card">
              <h3>Provider Readiness</h3>
              <ul className="shap-list">
                <li><span>Telemetry initialized:</span> <strong>{backendStatus?.telemetry?.available ? "Yes" : "No"}</strong></li>
                <li><span>Last provider update:</span> <strong>{backendStatus?.telemetry?.last_update ? new Date(backendStatus.telemetry.last_update).toLocaleTimeString() : "None"}</strong></li>
                <li><span>Incident registry:</span> <strong>{incidents.length ? "Operator-managed" : "No open incidents"}</strong></li>
                <li><span>Real flood model:</span> <strong>Not available</strong></li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT 4: SHELTER LOGISTICS MATRIX */}
      {activeTab === "shelters" && (
        <div className="eoc-shelters-view">
          <div className="shelters-header">
            <div>
              <h2>{selectedIncidentId ? "Incident shelter operations" : "Database shelter records"}</h2>
              <p>{selectedIncidentId
                ? "Responder-entered status and occupancy for this incident; values are not an external live sensor feed."
                : "Catalogue occupancy is not a live availability feed; freshness and incident association are not provided."}</p>
            </div>
            <div className="shelter-summary-tag">
              Shelters: <strong>{sheltersList.length}</strong> · Capacity: <strong>{stats.totalCapacity || "Not recorded"}</strong> · Occupancy: <strong>{stats.totalOccupied ?? (stats.occupancyKnownCount ? "Incomplete" : "Not reported")}</strong>
            </div>
          </div>
          {canModerate && selectedIncidentId && availableShelters.length > 0 && (
            <div className="eoc-incident-lifecycle">
              <label>
                Add a catalogue shelter to this incident
                <select
                  className="eoc-select"
                  value={selectedCatalogShelterId}
                  onChange={(event) => setSelectedCatalogShelterId(event.target.value)}
                >
                  <option value="">Select a shelter record</option>
                  {availableShelters.map((shelter) => (
                    <option key={shelter.id} value={shelter.id}>
                      {shelter.name} · {shelter.verification_status} · {shelter.source_name}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                className="button button-outline"
                disabled={!selectedCatalogShelterId}
                onClick={linkCatalogShelter}
              >
                Link shelter to incident
              </button>
            </div>
          )}
          <label className="eoc-control-group eoc-shelter-filter">
            <span className="eoc-label-small">RECORDED OCCUPANCY</span>
            <select
              className="eoc-select"
              value={shelterOccupancyFilter}
              onChange={(event) => setShelterOccupancyFilter(event.target.value)}
            >
              <option value="all">All records</option>
              <option value="high">85% or more</option>
              <option value="lower">Below 85%</option>
            </select>
          </label>
          <p className="catalog-disclaimer">
            {sheltersList.length
              ? selectedIncidentId
                ? "Values are scoped to this incident and include the latest operator timestamp. No external occupancy feed is connected."
                : "Occupancy values are database records only. Unverified or stale records must not be treated as confirmed availability."
              : selectedIncidentId
                ? "No shelters have been linked to this incident yet. A responder can add one by publishing an operational update."
                : "No shelter records were returned by the database. The dashboard is not showing static shelter locations."}
          </p>

          {sheltersList.length === 0 ? (
            <div className="eoc-empty-state">
              <strong>No database shelter records available</strong>
              <span>Records are shown only when returned by the backend.</span>
            </div>
          ) : filteredShelters.length === 0 ? (
            <div className="eoc-empty-state">
              <strong>No shelter records match this filter</strong>
              <span>Change the occupancy filter to see other catalogue records.</span>
            </div>
          ) : (
          <div className="shelters-grid">
            {filteredShelters.map((s) => {
              const occPct = s.capacity && s.occupied !== null
                ? Math.round((s.occupied / s.capacity) * 100)
                : null;
              const isHigh = occPct >= 85;
              const isMed = occPct >= 65;

              return (
                <div key={s.id} className={`shelter-card ${isHigh ? "shelter-card-high" : isMed ? "shelter-card-med" : ""}`}>
                  <div className="shelter-card-top">
                    <div>
                      <span className="shelter-district-badge">{s.district}</span>
                      <h4>{s.name}</h4>
                    </div>
                    <span className={`shelter-status-badge ${isHigh ? "status-high" : "status-ok"}`}>
                      {s.operationalStatus
                        ? s.operationalStatus.toUpperCase()
                        : s.occupied === null
                          ? "Occupancy unknown"
                          : s.capacity ? `${occPct}% recorded` : "Occupancy recorded"}
                    </span>
                  </div>

                  {occPct !== null && <div className="shelter-progress-bar" aria-label={`${occPct}% recorded occupancy`}>
                    <div
                      className="shelter-progress-fill"
                      style={{
                        width: `${Math.min(100, occPct)}%`,
                        backgroundColor: isHigh ? "#ff4d4f" : isMed ? "#faad14" : "#52c41a",
                      }}
                    />
                  </div>}

                  <div className="shelter-metrics">
                    <div>Occupancy: <strong>{s.occupied === null ? "Not reported" : `${s.occupied}${s.capacity ? ` / ${s.capacity}` : ""}`}</strong></div>
                    <div>Updated: <strong>{s.updatedAt ? new Date(s.updatedAt).toLocaleString() : "Not reported"}</strong></div>
                    <div>Verification: <strong>{s.verificationStatus || "unverified"}</strong></div>
                    <div>Source: <strong>{s.sourceName || "Database record"}</strong></div>
                    <div>Coordinates: <code>{Number(s.lat).toFixed(4)}, {Number(s.lon).toFixed(4)}</code></div>
                  </div>
                  {s.updateNote && <p className="catalog-disclaimer">{s.updateNote}</p>}
                  {canModerate && selectedIncidentId && (
                    <div className="eoc-shelter-update">
                      <label>
                        Status
                        <select
                          value={shelterUpdates[s.shelterId]?.status ?? s.operationalStatus ?? "unknown"}
                          onChange={(event) => setShelterUpdates({
                            ...shelterUpdates,
                            [s.shelterId]: {
                              ...shelterUpdates[s.shelterId],
                              status: event.target.value,
                            },
                          })}
                        >
                          <option value="unknown">Unknown</option>
                          <option value="open">Open</option>
                          <option value="limited">Limited</option>
                          <option value="closed">Closed</option>
                        </select>
                      </label>
                      <label>
                        Current occupancy
                        <input
                          type="number"
                          min="0"
                          max={s.capacity || 10000000}
                          value={shelterUpdates[s.shelterId]?.occupancy ?? (s.occupied ?? "")}
                          onChange={(event) => setShelterUpdates({
                            ...shelterUpdates,
                            [s.shelterId]: {
                              ...shelterUpdates[s.shelterId],
                              occupancy: event.target.value,
                            },
                          })}
                        />
                      </label>
                      <label>
                        Update note
                        <input
                          maxLength={500}
                          value={shelterUpdates[s.shelterId]?.note ?? s.updateNote}
                          onChange={(event) => setShelterUpdates({
                            ...shelterUpdates,
                            [s.shelterId]: {
                              ...shelterUpdates[s.shelterId],
                              note: event.target.value,
                            },
                          })}
                        />
                      </label>
                      <button
                        type="button"
                        className="button button-outline"
                        onClick={() => saveShelterUpdate(s)}
                      >
                        Publish update
                      </button>
                    </div>
                  )}
                  <button type="button" className="button button-outline" onClick={() => openFeature("shelter", s)}>
                    Show on map
                  </button>
                </div>
              );
            })}
          </div>
          )}
        </div>
      )}

      {activeTab === "catalog" && <GeographyCatalog />}

      {/* TAB CONTENT 6: MULTILINGUAL CAP ALERT BROADCASTER */}
      {activeTab === "broadcast" && (
        <div className="eoc-broadcast-view">
          <div className="broadcast-header">
            <div>
              <h2>Multilingual alert bulletin</h2>
              <p>Sample wording only. This view cannot send or authorize an alert.</p>
            </div>
          </div>

          <div className="broadcast-layout">
            <div className="broadcast-composer">
              <h3>Bulletin settings</h3>
              <div className="form-group">
                <label htmlFor="eoc-bulletin-area">Preview incident</label>
                <select
                  id="eoc-bulletin-area"
                  value={selectedIncidentId}
                  className="eoc-select"
                  disabled={!incidents.some((incident) => incident.status !== "closed")}
                  onChange={(event) => {
                    setSelectedIncidentId(event.target.value);
                    loadDashboard(false, event.target.value);
                  }}
                >
                  {incidents.filter((incident) => incident.status !== "closed").length === 0
                    ? <option value="">No active incident</option>
                    : incidents.filter((incident) => incident.status !== "closed").map((incident) => (
                      <option key={incident.id} value={String(incident.id)}>
                        {incident.title} · {incident.area_name}
                      </option>
                    ))}
                </select>
              </div>

              <div className="form-group">
                <label>Alert severity</label>
                <select
                  value={broadcastSeverity}
                  onChange={(e) => {
                    setBroadcastSeverity(e.target.value);
                    setBroadcastPrepared(false);
                  }}
                  className="eoc-select"
                >
                  <option value="extreme">High-urgency sample</option>
                  <option value="warning">Preparedness sample</option>
                </select>
              </div>

              <div className="broadcast-preview-boxes">
                <div className="preview-lang-box">
                  <div className="preview-lang-head">
                    <strong>English alert preview</strong>
                    <button
                      type="button"
                      className="btn-audio"
                      aria-label={speakingLanguage === "en" ? "Stop English speech" : "Listen to English alert"}
                      aria-pressed={speakingLanguage === "en"}
                      onClick={() => handleSpeechButton(CAP_BROADCAST_TEMPLATES[broadcastSeverity].en, "en")}
                    >
                      {speakingLanguage === "en"
                        ? speechUtteranceRef.current ? "Stop" : "Loading voice…"
                        : "🔊 Listen"}
                    </button>
                  </div>
                  <p>{CAP_BROADCAST_TEMPLATES[broadcastSeverity].en}</p>
                </div>

                <div className="preview-lang-box">
                  <div className="preview-lang-head">
                    <strong>Hindi alert preview</strong>
                    <button
                      type="button"
                      className="btn-audio"
                      aria-label={speakingLanguage === "hi" ? "Stop Hindi speech" : "Listen to Hindi alert"}
                      aria-pressed={speakingLanguage === "hi"}
                      onClick={() => handleSpeechButton(CAP_BROADCAST_TEMPLATES[broadcastSeverity].hi, "hi")}
                    >
                      {speakingLanguage === "hi"
                        ? speechUtteranceRef.current ? "Stop" : "Loading voice…"
                        : "🔊 Listen"}
                    </button>
                  </div>
                  <p>{CAP_BROADCAST_TEMPLATES[broadcastSeverity].hi}</p>
                </div>

                <div className="preview-lang-box">
                  <div className="preview-lang-head">
                    <strong>Maithili alert preview</strong>
                    <button
                      type="button"
                      className="btn-audio"
                      aria-label={speakingLanguage === "mai"
                        ? "Stop Maithili speech using a Hindi voice"
                        : "Listen to Maithili alert using a Hindi voice"}
                      aria-pressed={speakingLanguage === "mai"}
                      onClick={() => handleSpeechButton(CAP_BROADCAST_TEMPLATES[broadcastSeverity].mai, "mai")}
                    >
                      {speakingLanguage === "mai"
                        ? speechUtteranceRef.current ? "Stop" : "Loading voice…"
                        : "🔊 Listen (Hindi voice)"}
                    </button>
                  </div>
                  <p>{CAP_BROADCAST_TEMPLATES[broadcastSeverity].mai}</p>
                </div>
              </div>
              <p className="speech-status" role="status" aria-live="polite">
                {speechNotice}
              </p>

              <button
                className="btn-prepare-bulletin"
                onClick={() => setBroadcastPrepared(true)}
              >
                Review sample wording
              </button>

              {broadcastPrepared && (
                <div className="broadcast-success-banner">
                  <strong>Sample wording selected.</strong> No alert was created or sent.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
