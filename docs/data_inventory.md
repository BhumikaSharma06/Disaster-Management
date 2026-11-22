# AapdaSetu platform-wide data inventory

**Scope:** Pan-India, multi-hazard disaster preparedness, response, and recovery.
Flood is one hazard and a possible first data-ingestion pilot, not the scope of
the platform.

**Inventory checked:** 2026-11-19. Local raw-file statistics are in
[`data_audit_report.md`](./data_audit_report.md), generated from files present
under `ml/data/raw/`. This inventory records repository evidence and known
gaps; it does not certify external providers, permissions, or operational
fitness.

## Status and trust vocabulary

| Label | Meaning |
|---|---|
| `LOCAL / UNVERIFIED` | A file or prototype record is present locally, but its source, permission, fitness, or all of these are not confirmed. Presence is not approval to publish or use operationally. |
| `PLANNED / NOT ACQUIRED` | A source family is named in project plans, but no approved local dataset or connected feed is present. |
| `NOT IDENTIFIED` | The project has not yet selected a provider or confirmed an approved access method. |
| `DEMO ONLY` | Static interface content or a fixture; not a live feed or a verified source dataset. |
| `USER-SUBMITTED / NOT CONNECTED` | A future user-provided record type. No production intake or real records are currently connected. |
| `DERIVED / NOT OPERATIONAL` | A value produced by code or a model; it is not an authoritative observation or warning. |

Keep these evidence classes distinct in storage, APIs, and UI:

- **Source-issued warning/advisory:** retain issuer, issue time, validity period,
  affected area, update/cancellation state, and the original source reference.
- **Observation:** retain observation time, location/station, units, source,
  quality flags, and coverage.
- **Forecast/model output:** retain model/version, input window, forecast
  horizon, creation time, uncertainty, and validation status.
- **Resource listing:** retain source, location, capacity/details, observation
  or review time, and freshness. A mapped facility is not thereby open,
  accessible, or available.
- **Event or impact report:** distinguish official reports from community
  reports and preserve review state.
- **User-submitted request/offer:** treat as sensitive operational data with
  consent, access, retention, deletion, and abuse controls.
- **Prototype/demo:** label visibly and keep out of operational decisions.

## Platform-wide source and dataset matrix

| Data family | What the application needs | Current repository evidence | Source/access/rights state | Next validation or acquisition action |
|---|---|---|---|---|
| Administrative geography | Versioned national/state/district and, where licensed and useful, finer boundaries; stable IDs; geometry CRS; valid dates. | PostGIS `Region` model and read-only catalog exist. The optional seed script contains approximate Lower Kosi prototype polygons. No approved boundary file is present in `ml/data/raw/`. | `NOT IDENTIFIED` for a production boundary dataset. Source vintage, authority, terms, and redistribution rights are unconfirmed. | Identify candidate custodians and exact dataset/vintage; obtain terms and attribution requirements; check topology, CRS, identifiers, and update process before import. |
| Population, buildings, infrastructure, and other exposure | Aggregated, appropriately licensed exposure layers with geography, vintage, resolution, and uncertainty. | No exposure dataset or connected API was found in the repository. | `NOT IDENTIFIED`; access, privacy implications, and permitted aggregation are unknown. | Decide which exposure variables are necessary per use case; identify authorized sources and privacy-safe resolution; do not collect personal data by default. |
| Flood observations and discharge | Station-linked stage/discharge, units/datum, station identity, timestamps, quality flags, and historical coverage. | Five local CSV files are listed in the audit report. Birpur Barrage is a configured discharge candidate; Baisi_1 has no confirmed Kosi attribution. No training result is treated as real/validated. | `LOCAL / UNVERIFIED`. Original provider, acquisition method, license, official station IDs, and operational status are not established by repository documentation. | Obtain source documentation and permission; verify station identity, units/datum, time coverage, missingness, and Birpur danger threshold before model use. |
| Rainfall and general weather | Historical/forecast precipitation and relevant weather variables with units, grid/station metadata, issue/valid times, and coverage. | No rainfall/weather data file is present. IMD rainfall is named as a planned replay input; no feed is connected. | `PLANNED / NOT ACQUIRED`. Exact product, access conditions, license, and update cadence are not confirmed. | Select the required variables and temporal/spatial resolution; confirm authorized archive or service access and terms; capture forecast issue time separately from valid time. |
| Cyclone, severe storm, lightning, heatwave, cold wave | Hazard-specific observations and source-issued forecasts/warnings, each with severity, affected area, issue/expiry/update time. | The UI has static safety guidance. No observation or warning feed is connected. | `NOT IDENTIFIED` for approved source datasets/feeds; no live claim is supported. | Identify the competent source for each warning type and region; document exact products, access/redistribution terms, latency, expiry, cancellations, and fallback behavior. |
| Earthquake and tsunami | Seismic event observations and, where authorized, official tsunami warning/advisory records with location, magnitude/intensity or alert level, issue/valid times, and revisions. | Hazard cards/guidance only; no event feed, warning feed, or observation archive is present. | `NOT IDENTIFIED`; source contracts and allowed reuse have not been established. | Research authoritative source products separately; record whether each is observation, event report, forecast, or warning; verify update and cancellation semantics. |
| Landslide and avalanche | Event inventories, susceptibility/exposure layers, and official advisories with geometry, date, and scale/uncertainty. | No corresponding data files or connected services are present. | `NOT IDENTIFIED`; no source, coverage, or licensing decision recorded. | Determine which regions and decisions are in scope; identify licensed event and terrain data and competent warning sources; document resolution and limitations. |
| Drought | Long-duration rainfall, soil moisture, reservoir/water availability, vegetation or agricultural indicators, and official drought assessments as appropriate. | No drought observation, assessment, or forecast datasets are present. | `NOT IDENTIFIED`; variable definitions, product rights, and update schedules are unknown. | Define the intended drought indicator and scale first; then select authorized inputs with documented baselines, units, and temporal aggregation. |
| Wildfire | Fire detections/events, perimeters, weather/fuel context, and official evacuation/advisory information where available. | Static safety guidance only; no fire data or feed is connected. | `NOT IDENTIFIED`; provider, latency, detection confidence, and reuse conditions are unknown. | Identify approved event and warning sources; retain observation time/confidence and do not equate satellite detection with a confirmed incident. |
| Industrial, chemical, and other human-made incidents | Authorized incident records, affected-area advisories, facility context where permitted, and authoritative response updates. | Hazard guidance exists in the UI; no incident dataset/feed is present. | `NOT IDENTIFIED`. Facility/security-sensitive information may have access and disclosure restrictions. | Work with authorized custodians; classify sensitive fields, access rules, and publication boundaries before collecting or displaying records. |
| Public-health emergency | Aggregated, authoritative advisories/surveillance suitable for public communication; geography and publication time. | Static safety guidance only; no health dataset or feed is connected. | `NOT IDENTIFIED`. Health data has heightened privacy and disclosure risk; no individual health data source is approved. | Limit to authorized public advisories and appropriately aggregated data; confirm source, privacy review, publication rules, and update/correction process. |
| Official warnings and advisories (cross-hazard) | Issuer, hazard, affected geography, issue/valid/expiry time, severity, language, revision/cancellation, source link/reference. | Static alert/bulletin text in the operations-center demo; alert model exists but no official feed or mock delivery workflow is connected. | `DEMO ONLY` for UI content; no official warning source or dispatch integration is active. | Inventory products per hazard/authority; define a source adapter and lifecycle semantics; keep source warnings distinct from model predictions and user reports. |
| Flood extent and disaster event/impact history | Georeferenced event footprints, observation/event time, product method, confidence, and impact definitions for validation and exposure analysis. | No such dataset is present. ISRO MOSDAC/Bhuvan flood extent is named as a planned input, not a confirmed acquisition. | `PLANNED / NOT ACQUIRED`; exact product, access method, terms, and coverage remain TODOs. | Confirm an authorized archived product, product version and observation time; establish whether it represents observed extent, interpretation, or reported impact. |
| Shelters, hospitals, clinics, emergency services, and other facilities | Stable identifier, coordinates, type, responsible operator, contact where approved, capacity, accessibility, operating/availability time, and last confirmation. | Shelter model, read-only API, and catalog exist. Optional seed script has prototype shelter entries; static demonstration entries are separate. No approved real facility dataset or hospital catalog is connected. | `LOCAL / UNVERIFIED` for project seed/demo records; `NOT IDENTIFIED` for approved operational facility data. Source, license, capacity, and current availability are unconfirmed. | Identify responsible owners and approved records; define field-specific review and freshness; never infer open/available status from presence in catalog. |
| Roads, bridges, routes, and closures | Licensed routable network with extract/version date, restrictions, accessibility attributes, and time-bounded official/community closure reports. | No local road extract or route service is connected. OpenStreetMap is named as a planned road/shelter input only. | `PLANNED / NOT ACQUIRED`. OSM data is under ODbL; confirm attribution and applicable share-alike obligations for the intended database/use. No live closure feed is identified. | Choose static/offline versus service-based routing; acquire an appropriately dated extract under its terms; identify closure source and reporting/review process before route advice. |
| SOS requests and volunteer offers | User-submitted need/capacity, location, urgency/status, consent, reporter/contact handling, duplicate signals, review and audit history. | Frontend forms and response views are local demonstrations; backend domain models exist, but real submissions/APIs are not connected. | `USER-SUBMITTED / NOT CONNECTED`. No production collection, authentication, consent, retention, deletion, or abuse controls are implemented. | Complete privacy/threat/access/retention design and incident workflow before enabling collection; do not treat demo forms as real requests. |
| Safety guidance, language, and accessibility content | Reviewed hazard- and lifecycle-specific text, language/region, source/reviewer, version, effective date, and translation provenance. | English guidance and limited local translation/cache behavior are in the frontend. Bhashini credentials/endpoints are not configured; no translation requests are active. | `DEMO ONLY`/locally bundled content; content review and source lineage are not fully represented as a managed dataset. | Assign content source/reviewer and version metadata; verify translations with qualified reviewers; preserve English fallback and avoid implying machine translation is validated. |
| Model outputs and derived risk | Versioned predictions or risk scores with input lineage, issue time, horizon, uncertainty, validation and status. | Hazard/risk model scaffolding and data processing exist. No real model metrics or operational prediction API exists. Seed-derived or UI values must not be presented as validated predictions. | `DERIVED / NOT OPERATIONAL`. No validated model output qualifies for application decisions. | Do not publish a risk output until source inputs, model version, temporal/spatial validation, uncertainty, and fallback rules are documented. |

## Local flood-data files currently present

The following is a file-presence and content audit, not a source or license
certification. Exact observed ranges below come from
[`data_audit_report.md`](./data_audit_report.md). Some filenames imply date
periods that do not match their contents; use observed timestamps, not the
filename, as the evidence.

| Local file | Audit evidence | Known issue / decision |
|---|---|---|
| `ml/data/raw/bihar_sw_daily_discharge_manual.csv` | 52,093 rows; 2020-06-15 to 2025-05-31; discharge in M3/s; includes Birpur Barrage and other named sites. | Source attribution and license are undocumented. Birpur official station ID and danger threshold remain unknown. Presence does not establish a CWC/India-WRIS origin. |
| `ml/data/raw/rwl_tel_hr_bihar_999_2021_2025.csv` | 821,160 rows; 2021-09-08 to 2025-12-31; multi-station water-level telemetry; 51 detected gaps in the audit. | Provider/terms are undocumented. Station-to-river/basin mapping needs confirmation; Baisi_1 has no river/basin attribution and is not an established Kosi target. |
| `ml/data/raw/rwl_tel_hr_bihar_999_2026_2030.csv` | 108,614 rows; 2026-01-01 to 2026-11-17; multi-station water-level telemetry; one detected gap. | Filename range extends beyond observed records. Not a live feed; source, terms, station attribution, and update process are unconfirmed. |
| `ml/data/raw/rwl_tele_hr_bihar_999_1961_1990.csv` | 14 rows; observed dates 1969-12-31 to 1970-10-06. | Observed coverage does not match the broad filename range; inspect source export and do not assume a 1961-1990 history. |
| `ml/data/raw/rwl_tele_hr_bihar_999_1991_2020.csv` | 237 rows; observed dates 1999-11-30 to 2000-04-11; 115 detected gaps in the audit. | Observed coverage does not match the broad filename range; inspect source export and do not assume a 1991-2020 history. |

No rainfall, approved administrative-boundary, DEM, flood-extent, OSM extract,
facility, public-warning, or other-hazard observation dataset was found in the
local raw-data directory when this inventory was checked.

## Candidate sources named in project plans

These are investigation targets, not claims that access is currently available:

| Candidate | Intended family | Current state | Must confirm before use |
|---|---|---|---|
| Archived IMD rainfall | Flood/weather observations | Named as a planned replay input; no local file or configured access. | Product and units, archive/access method, license/redistribution, coverage, time conventions, and attribution. |
| CWC gauge/discharge | River observations | Named as a planned source family; local CSV provenance does not establish CWC origin. | Station IDs, source authenticity, units/datum, archive access, license/terms, and update behavior. |
| ISRO MOSDAC/Bhuvan flood extent | Observed flood extent | Named as a planned replay input; no local product. | Exact product, date/coverage, access conditions, terms, processing/quality, and correct interpretation. |
| OpenStreetMap | Roads and possible facility locations | Named as a planned input; no local extract. | Extract date/coverage, ODbL obligations, attribution/share-alike handling, and field completeness. |

For other hazard-specific sources, the repository does not yet identify a
provider or approved product. Identify an authoritative custodian and exact
dataset/feed per hazard rather than inferring a source or reusing flood
assumptions.

## First-pilot decision gate

**No dataset is currently cleared by this inventory for operational use.** The
local discharge archive is a plausible first *technical* ingestion pilot only
if its source and permitted use can be documented. If that cannot be confirmed,
select another dataset only after the same evidence is available.

Select the pilot by checking:

1. identifiable source/custodian and written or published permission for the
   intended use;
2. documented license, attribution, and redistribution limits;
3. adequate coverage, stable identifiers, data dictionary, units, timestamps,
   and known quality limits;
4. a reproducible local sample/export or authorized access method;
5. a safe, non-operational pilot use and a way to test invalid/stale data.

Until those checks pass, keep data local and unserved, or use explicitly
synthetic fixtures in tests only. Do not invent source URLs, scrape restricted
portals, or label a local file "live".

## Milestone 1 completion

This inventory covers the platform's data families and user-generated records,
records the local files and their observed ranges, distinguishes source-issued
warnings/observations/model outputs/resources/reports/demo content, and lists
authorization and validation gaps. The **platform-wide inventory is complete
as a repository baseline**. External source authorization and a first real-data
pilot remain unconfirmed. Milestones 2-4 now provide shared registry
contracts, offline validation and quarantined staging for region/shelter
GeoJSON, and read-only catalog visibility. These controls do not establish
source accuracy, rights, or operational fitness. Milestone 5 and operational
use remain paused until an approved dataset is available; hazard-specific
ingestion paths are still needed across the broader platform.
