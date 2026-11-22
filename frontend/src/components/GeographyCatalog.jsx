import { useEffect, useState } from "react";

import {
  getDatasetImports,
  getRegions,
  getShelters,
} from "../api/geography.js";

function formatCoordinates(point) {
  const [longitude, latitude] = point.coordinates;
  return `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;
}

function VerificationBadge({ record }) {
  const statusLabel = record.verification_status.replaceAll("_", " ");
  return (
    <span className={`catalog-verification catalog-verification-${record.verification_status}`}>
      {statusLabel}
    </span>
  );
}

function DataState({ status, error, emptyMessage }) {
  if (status === "loading") {
    return <p className="catalog-state" role="status">Loading database records…</p>;
  }
  if (status === "error") {
    return <p className="catalog-state catalog-error" role="alert">{error}</p>;
  }
  if (status === "success" && emptyMessage) {
    return <p className="catalog-state">{emptyMessage}</p>;
  }
  return null;
}

function formatStatus(status) {
  return status.replaceAll("_", " ");
}

function DatasetRegistry({ datasets, status, error }) {
  return (
    <section className="catalog-panel catalog-dataset-registry" aria-labelledby="datasets-title">
      <h3 id="datasets-title">Imported dataset registry</h3>
      <p className="catalog-registry-note">
        Imported files remain staged and are not used by hazard, routing, warning,
        or shelter workflows. A successful import means structural checks passed,
        not that source rights or operational fitness were approved. Rights
        references are operator-supplied and are not independently verified.
      </p>
      <DataState
        status={status}
        error={error}
        emptyMessage={datasets.length === 0 ? "No dataset imports are registered." : ""}
      />
      {status === "success" && datasets.length > 0 && (
        <div className="catalog-table-wrap">
          <table className="catalog-table">
            <thead>
              <tr>
                <th scope="col">Dataset</th>
                <th scope="col">Source / rights</th>
                <th scope="col">Coverage / period</th>
                <th scope="col">Freshness</th>
                <th scope="col">Validation</th>
                <th scope="col">Review</th>
                <th scope="col">Publication</th>
                <th scope="col">Records</th>
              </tr>
            </thead>
            <tbody>
              {datasets.map((dataset) => (
                <tr key={dataset.id}>
                  <td>
                    <span className="catalog-source">{dataset.dataset_key}</span>
                    <span className="catalog-source-reference">
                      {dataset.dataset_family.replaceAll("_", " ")} /{" "}
                      {dataset.evidence_type.replaceAll("_", " ")}
                    </span>
                    <span className="catalog-source-reference">{dataset.file_name}</span>
                  </td>
                  <td>
                    <span className="catalog-source">{dataset.source_name}</span>
                    {dataset.source_reference && (
                      <span className="catalog-source-reference">{dataset.source_reference}</span>
                    )}
                    <span className="catalog-source-reference">
                      Rights: {formatStatus(dataset.rights_status)}
                    </span>
                    {dataset.source_license && (
                      <span className="catalog-source-reference">
                        License: {dataset.source_license}
                      </span>
                    )}
                    {dataset.rights_reference && (
                      <span className="catalog-source-reference">
                        Rights reference: {dataset.rights_reference}
                      </span>
                    )}
                  </td>
                  <td>
                    <span>{dataset.coverage}</span>
                    <span className="catalog-source-reference">
                      {dataset.period_start ?? "Start unknown"} – {dataset.period_end ?? "End unknown"}
                    </span>
                  </td>
                  <td>
                    <span className={`catalog-verification catalog-verification-${dataset.freshness_status}`}>
                      {formatStatus(dataset.freshness_status)}
                    </span>
                    <span className="catalog-source-reference">
                      {dataset.source_updated_at
                        ? new Date(dataset.source_updated_at).toLocaleString()
                        : "Source update time not supplied"}
                    </span>
                  </td>
                  <td>
                    {formatStatus(dataset.validation_status)}
                    {typeof dataset.validation_report?.rejected_feature_count === "number"
                      && dataset.validation_report.rejected_feature_count > 0 && (
                        <span className="catalog-source-reference">
                          {dataset.validation_report.rejected_feature_count} rejected
                        </span>
                      )}
                  </td>
                  <td>{formatStatus(dataset.review_status)}</td>
                  <td>{formatStatus(dataset.publication_status)}</td>
                  <td>{dataset.record_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default function GeographyCatalog() {
  const [regions, setRegions] = useState([]);
  const [regionsStatus, setRegionsStatus] = useState("loading");
  const [regionsError, setRegionsError] = useState("");
  const [shelters, setShelters] = useState([]);
  const [sheltersStatus, setSheltersStatus] = useState("loading");
  const [sheltersError, setSheltersError] = useState("");
  const [datasets, setDatasets] = useState([]);
  const [datasetsStatus, setDatasetsStatus] = useState("loading");
  const [datasetsError, setDatasetsError] = useState("");
  const [selectedRegionId, setSelectedRegionId] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setRegionsStatus("loading");
    setRegionsError("");

    getRegions(controller.signal)
      .then((data) => {
        setRegions(data);
        setRegionsStatus("success");
      })
      .catch((error) => {
        if (error.name === "AbortError") return;
        setRegionsError("Could not load regions. Check the API connection and retry.");
        setRegionsStatus("error");
      });

    return () => controller.abort();
  }, [reloadKey]);

  useEffect(() => {
    const controller = new AbortController();
    setSheltersStatus("loading");
    setSheltersError("");
    setShelters([]);

    getShelters(selectedRegionId, controller.signal)
      .then((data) => {
        setShelters(data);
        setSheltersStatus("success");
      })
      .catch((error) => {
        if (error.name === "AbortError") return;
        setSheltersError("Could not load shelters. Check the API connection and retry.");
        setSheltersStatus("error");
      });

    return () => controller.abort();
  }, [selectedRegionId, reloadKey]);

  useEffect(() => {
    const controller = new AbortController();
    setDatasetsStatus("loading");
    setDatasetsError("");

    getDatasetImports(controller.signal)
      .then((data) => {
        setDatasets(data);
        setDatasetsStatus("success");
      })
      .catch((error) => {
        if (error.name === "AbortError") return;
        setDatasetsError("Could not load dataset registry. Check the API connection and retry.");
        setDatasetsStatus("error");
      });

    return () => controller.abort();
  }, [reloadKey]);

  const refreshing =
    regionsStatus === "loading"
    || sheltersStatus === "loading"
    || datasetsStatus === "loading";

  return (
    <section className="eoc-catalog-view" aria-labelledby="catalog-title">
      <header className="catalog-header">
        <div>
          <h2 id="catalog-title">Database geography catalog</h2>
          <p>Read-only records returned by the AapdaSetu API.</p>
        </div>
        <button
          className="catalog-refresh"
          type="button"
          onClick={() => setReloadKey((key) => key + 1)}
          disabled={refreshing}
        >
          {refreshing ? "Loading…" : "Refresh"}
        </button>
      </header>

      <p className="catalog-disclaimer">
        Local database records only. Their presence does not verify a
        location, its capacity, or its operational status. Do not use this
        catalog for emergency navigation or evacuation decisions. “Verified”
        means a reviewer recorded a source and review time; it is not a live
        safety or availability guarantee.
      </p>

      <div className="catalog-grid">
        <DatasetRegistry
          datasets={datasets}
          status={datasetsStatus}
          error={datasetsError}
        />
        <section className="catalog-panel" aria-labelledby="regions-title">
          <h3 id="regions-title">Regions</h3>
          <DataState
            status={regionsStatus}
            error={regionsError}
            emptyMessage={regions.length === 0 ? "No region records are available." : ""}
          />
          {regionsStatus === "success" && regions.length > 0 && (
            <div className="catalog-table-wrap">
              <table className="catalog-table">
                <thead>
                  <tr>
                    <th scope="col">Name</th>
                    <th scope="col">Type</th>
                    <th scope="col">District</th>
                    <th scope="col">Boundary</th>
                    <th scope="col">Verification</th>
                    <th scope="col">Source / reference / license</th>
                  </tr>
                </thead>
                <tbody>
                  {regions.map((region) => (
                    <tr key={region.id}>
                      <td>{region.name}</td>
                      <td>{region.region_type}</td>
                      <td>{region.district_name}</td>
                      <td>{region.boundary.type}</td>
                      <td><VerificationBadge record={region} /></td>
                      <td>
                        <span className="catalog-source">{region.source_name}</span>
                        {region.source_reference && (
                          <span className="catalog-source-reference">{region.source_reference}</span>
                        )}
                        {region.source_license && (
                          <span className="catalog-source-reference">License: {region.source_license}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="catalog-panel" aria-labelledby="shelters-title">
          <div className="catalog-panel-header">
            <h3 id="shelters-title">Shelters</h3>
            <label>
              Filter by region
              <select
                value={selectedRegionId}
                onChange={(event) => setSelectedRegionId(event.target.value)}
                disabled={regionsStatus !== "success"}
              >
                <option value="">All regions</option>
                {regions.map((region) => (
                  <option key={region.id} value={region.id}>
                    {region.name} — {region.district_name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <DataState
            status={sheltersStatus}
            error={sheltersError}
            emptyMessage={shelters.length === 0 ? "No shelter records match this selection." : ""}
          />
          {sheltersStatus === "success" && shelters.length > 0 && (
            <div className="catalog-table-wrap">
              <table className="catalog-table">
                <thead>
                  <tr>
                    <th scope="col">Name</th>
                    <th scope="col">Region ID</th>
                    <th scope="col">Capacity</th>
                    <th scope="col">Recorded occupancy</th>
                    <th scope="col">Coordinates (lat, lon)</th>
                    <th scope="col">Verification</th>
                    <th scope="col">Source / reference / license</th>
                  </tr>
                </thead>
                <tbody>
                  {shelters.map((shelter) => (
                    <tr key={shelter.id}>
                      <td>{shelter.name}</td>
                      <td>{shelter.region_id ?? "—"}</td>
                      <td>{shelter.capacity ?? "Not recorded"}</td>
                      <td>{shelter.current_occupancy}</td>
                      <td>{formatCoordinates(shelter.location)}</td>
                      <td><VerificationBadge record={shelter} /></td>
                      <td>
                        <span className="catalog-source">{shelter.source_name}</span>
                        {shelter.source_reference && (
                          <span className="catalog-source-reference">{shelter.source_reference}</span>
                        )}
                        {shelter.source_license && (
                          <span className="catalog-source-reference">License: {shelter.source_license}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </section>
  );
}
