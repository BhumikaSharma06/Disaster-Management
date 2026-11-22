import { useEffect, useRef, useState } from "react";

import { createSosRequest, getIncidents } from "../api/eoc.js";
import "./SosReportForm.css";

function newSubmissionId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (character) => {
    const random = Math.floor(Math.random() * 16);
    return (character === "x" ? random : (random & 0x3) | 0x8).toString(16);
  });
}

export default function SosReportForm() {
  const [incidents, setIncidents] = useState([]);
  const [incidentLoadError, setIncidentLoadError] = useState("");
  const [incidentId, setIncidentId] = useState("");
  const [location, setLocation] = useState(null);
  const [locationError, setLocationError] = useState("");
  const [formError, setFormError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const submissionIdRef = useRef(null);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    async function refreshIncidents() {
      try {
        const records = await getIncidents(controller.signal);
        if (active) {
          setIncidents(records.filter((incident) => incident.status !== "closed"));
          setIncidentLoadError("");
        }
      } catch (error) {
        if (active && error.name !== "AbortError") {
          setIncidentLoadError(error.message || "Could not load active incidents.");
        }
      }
    }

    refreshIncidents();
    const intervalId = window.setInterval(refreshIncidents, 15000);
    return () => {
      active = false;
      window.clearInterval(intervalId);
      controller.abort();
    };
  }, []);

  function requestLocation() {
    setLocationError("");
    if (!navigator.geolocation) {
      setLocationError("Location access is not available in this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => setLocation({
        latitude: coords.latitude,
        longitude: coords.longitude,
      }),
      () => setLocationError("Could not get your location. Check permission and try again."),
      { enableHighAccuracy: false, timeout: 10000 },
    );
  }

  async function submit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    setFormError("");
    setSuccess("");
    if (!location) {
      setFormError("Share your location before submitting an SOS report.");
      return;
    }
    setSubmitting(true);
    const values = Object.fromEntries(new FormData(form));
    if (!submissionIdRef.current) submissionIdRef.current = newSubmissionId();
    try {
      const result = await createSosRequest({
        client_submission_id: submissionIdRef.current,
        incident_id: incidentId ? Number(incidentId) : null,
        need_type: values.need_type,
        description: values.description,
        urgency: values.urgency,
        people_affected: values.people_affected ? Number(values.people_affected) : null,
        latitude: location.latitude,
        longitude: location.longitude,
      });
      setSuccess(`SOS report recorded as SOS-${result.id}.`);
      submissionIdRef.current = null;
      form.reset();
      setIncidentId("");
      setLocation(null);
    } catch (error) {
      setFormError(error.message || "SOS report could not be submitted. Please retry.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="sos-report-card" aria-labelledby="sos-report-title">
      <div>
        <p className="sos-report-eyebrow">EMERGENCY DISTRESS REPORT</p>
        <h2 id="sos-report-title">Send an SOS report</h2>
        <p>Reports appear in the operations dashboard for the selected incident. For immediate danger, call 112.</p>
      </div>
      <form onSubmit={submit}>
        <label>
          Active incident (optional)
          <select value={incidentId} onChange={(event) => setIncidentId(event.target.value)}>
            <option value="">Not linked to an incident</option>
            {incidents.map((incident) => (
              <option key={incident.id} value={incident.id}>
                {incident.title} · {incident.hazard_type} · {incident.area_name}
              </option>
            ))}
          </select>
        </label>
        {incidentLoadError && <p className="sos-report-error" role="alert">{incidentLoadError}</p>}
        <div className="sos-report-fields">
          <label>
            Type of help needed
            <input name="need_type" required maxLength={64} placeholder="Medical, evacuation, food…" />
          </label>
          <label>
            Urgency
            <select name="urgency" defaultValue="urgent">
              <option value="urgent">Urgent</option>
              <option value="high">High</option>
              <option value="general">General</option>
            </select>
          </label>
          <label>
            People affected (optional)
            <input name="people_affected" type="number" min="1" max="100000" />
          </label>
          <label className="sos-report-description">
            Details
            <textarea name="description" required maxLength={4000} rows="3" />
          </label>
        </div>
        <div className="sos-report-location">
          <button type="button" className="button button-outline" onClick={requestLocation}>
            {location ? "Update location" : "Share current location"}
          </button>
          <span>
            {location
              ? `Location ready · ${location.latitude.toFixed(4)}, ${location.longitude.toFixed(4)}`
              : "Location is requested only after you choose this button."}
          </span>
        </div>
        {locationError && <p className="sos-report-error" role="alert">{locationError}</p>}
        {formError && <p className="sos-report-error" role="alert">{formError}</p>}
        {success && <p className="sos-report-success" role="status">{success}</p>}
        <button type="submit" className="button button-primary" disabled={submitting}>
          {submitting ? "Sending…" : "Submit SOS"}
        </button>
      </form>
    </section>
  );
}
