# AapdaSetu — Application Capabilities and Future Scope

## Document Purpose and Scope

This document describes the implemented state of **AapdaSetu**, a disaster-management application for communities across India. It is based on the repository source, project configuration, tests, data audit, and documentation available in this workspace. It separates working capabilities from demonstrations, scaffolding, placeholders, and proposed future work.

AapdaSetu is a prototype and preparedness platform. It is **not** an emergency service, an official warning system, or a source of verified live evacuation information.

---

## 1. Application Overview

### Primary purpose

AapdaSetu follows the vision **“Swadeshi for Aatmanirbhar Bharat”** and aims to organize disaster information across the complete lifecycle:

- **Before:** general preparedness information, regional-language presentation, and future local risk forecasting.
- **During:** hazard-specific safety guidance, emergency contacts, location sharing, and future verified routing and shelters.
- **After:** a concept for collecting needs and volunteer capacity and matching support requests.

The current implementation is primarily a responsive educational and preparedness interface. The backend and machine-learning code provide selected structural and data-processing foundations, but live operational workflows are not connected.

### Intended users

- Citizens seeking general disaster safety instructions.
- Families planning household preparedness and communication.
- Emergency-management students and local response teams evaluating the concept.
- Researchers and developers working with the flood data-processing and training scaffold.
- Project evaluators, academic demonstrators, and viva reviewers.

### Practical situations

The application can currently be used to:

- review Before/During/After instructions for 14 disaster categories;
- find 112 and, where relevant, 108 or 101 from the displayed guide;
- manually copy or share a device location after explicit user action;
- preview whether a local browser/offline status indicator is online or offline;
- review an SOS/response, shelter, hydrograph, and map-style operations-center demonstration;
- inspect local flood-data readiness and the status of supplied datasets;
- run the backend health check and flood-feature unit tests;
- develop or evaluate a future flood forecast from supplied real data.

### Core value proposition

AapdaSetu is designed to make disaster readiness more accessible through all-hazard coverage, a disaster-lifecycle structure, simple language, local emergency-number links, and a pan-India interface design. Its differentiation is conceptual rather than operational: hazard modules, regional localization, geographic models, and SOS matching are intended to share a common platform rather than becoming isolated systems.

The present differentiation is mostly architectural—shared hazard, region, shelter, SOS, volunteer, alert, translation, and matching concepts are separated in the codebase—even though most operational components remain unimplemented.

---

## 2. Existing Application Capabilities

### 2.1 Main user interface and navigation

**What it does**

The React/Vite frontend presents an Overview, Prepare, During, Response, Data, and Operations Center view. It also provides a mobile navigation experience and a browser connectivity indicator.

**User workflow**

Users choose an item from the sidebar or mobile navigation. The selected view is rendered inside the main application shell. The language selector changes the interface to English or Hindi where translations exist.

**Internal behavior**

The application uses React state to control the active view, selected hazard, language, mobile menu, and local form state. It listens to browser `online` and `offline` events. Navigation is client-side; the operations-center Database Catalog tab calls the read-only region and shelter API.

**Inputs and outputs**

- Inputs: navigation choice, hazard selection, language selection, browser connectivity state.
- Outputs: the corresponding page, selected hazard label, language-specific text, and online/offline display.

**Contribution**

This is the common presentation shell through which all implemented user-facing modules are exposed.

### 2.2 All-hazard overview and lifecycle readiness

**What it does**

The overview explains the Before/Prepare, During/Safety, and After/Response lifecycle and offers a status board, preparedness checklist, and hazard module directory.

**Implemented data**

The application contains guidance for 14 hazard categories:

- Flood
- Cyclone
- Earthquake
- Landslide
- Drought
- Heatwave
- Tsunami
- Wildfire
- Lightning
- Severe storm
- Avalanche
- Industrial or chemical incident
- Public-health emergency
- Cold wave

**User workflow**

Users can select a hazard card. Selecting a card opens the During view and opens that hazard's safety guide. Overview cards and the lifecycle strip navigate to relevant screens.

**Internal behavior**

Hazard data is loaded from `frontend/src/data/hazards.js`, which contains titles, icons, focus descriptions, and hazard-specific Before/During/After guidance.

**Inputs and outputs**

- Inputs: hazard selection and lifecycle navigation.
- Outputs: hazard-specific cards, general preparedness steps, and navigation into the safety guide.

**Contribution**

This provides broad, accessible preparedness coverage without falsely presenting the information as a live warning feed.

### 2.3 Hazard safety guides

**What it does**

The During view expands a compact safety guide inside each hazard card. Each open guide contains a phase table and relevant emergency contacts.

**User workflow**

The user selects **View safety guide**. The card shows Before, During, and After actions in a table. The guide can be closed directly.

**Inputs and outputs**

- Inputs: selected hazard and display language.
- Outputs: phased safety instructions, fallback language notice, and phone links for emergency services.

**Internal behavior**

The guide reads structured hazard objects and returns relevant contacts based on hazard ID. The emergency number 112 is the general fallback. Ambulance and fire links are 108 and 101 respectively where configured.

**Contribution**

This is one of the application's strongest implemented capabilities: general safety information is available without a backend or live data dependency.

### 2.4 Language and localization behavior

**What it does**

English is the default. The interface offers English and Hindi. When a user enables location detection, a country-level approximate lookup determines whether India is supported and filters the language choices.

**User workflow**

A manual language selector remains available. Hindi may be selected, and supported short interface labels are translated locally. Most uncached safety text remains in English.

**Internal behavior**

- `deviceLanguage.js` checks an approximate India latitude/longitude bounding box.
- It does not perform reverse geocoding or identify an exact district or state.
- `translation.js` has a small local cache for phase names and selected contact labels.
- Cache misses remain unchanged in English and show a fallback notice.

**Inputs and outputs**

- Inputs: browser region detection consent or manual selection.
- Outputs: language options and translated/cached text; uncached text is unchanged English.

**Limit of the implementation**

Bhashini credentials and pipeline endpoints are not configured, and the backend Bhashini client is only a placeholder. There is no live translation request, translation cache persistence, or automated full-guide translation.

### 2.5 User-controlled location sharing

**What it does**

The user can explicitly request their browser coordinates. When obtained, the page displays latitude, longitude, and approximate accuracy. The user may share through the browser share sheet or copy the location text.

**User workflow**

1. The user chooses **Share my location** or an equivalent request button.
2. The browser asks for geolocation permission.
3. On success, coordinates appear in the page.
4. The user chooses device sharing or clipboard copying.

**Internal behavior**

Coordinates are held only in React component state. They are not automatically sent to an API and are not persisted. The page uses no automatic geolocation request for this feature.

**Inputs and outputs**

- Inputs: explicit user action and browser geolocation permission.
- Outputs: formatted coordinates, accuracy, share status, copy status, or an unavailable-permission message.

**Contribution**

This demonstrates responsible user consent and provides a local coordination utility, but it does not transmit an SOS or send coordinates to responders.

### 2.6 Persistent help requests and supply coordination

**What it does**

The **Get or offer help** view accepts structured submissions for:

- a quantity-bearing help request; and
- a supply offer against an open request item.

Requests include item, urgency, required units and unit label, state/district,
village or ward, optional landmark, contact details, notes, and geocoded
coordinates. The backend stores an SRID 4326 PostGIS point and request item
totals. The donor form lists open items with required, fulfilled, and remaining
quantities. Supply offers record donor contact details and pickup location.

**User workflow**

Community members submit a help request or select an open request item and
submit a supply offer. When signed in, each submission is associated with that
account and appears in its persistent request or offer history; the user can
check status and cancel an active request or an undelivered offer. Guest
submissions remain supported but cannot be managed from an account history.
Verified responders and administrators can filter the shared Responder inbox by
status, item, or location; the inbox includes active help requests as well as
supply offers. Responders can inspect requester and donor contacts plus
pickup/drop locations, claim offers, and advance each assignment from
contacted to picked up to delivered. At pickup, the responder confirms the
actual quantity received, which may be lower than the pledge. The offer's
donor, assigned responder, or an administrator can cancel an active offer.
The EOC dashboard displays current request, offer, fulfillment, and assignment
metrics and recent records; responders and administrators can flag or close
requests as spam or duplicates.

**Internal behavior**

FastAPI writes requests, items, offers, and responder assignments to PostgreSQL
through SQLAlchemy and Alembic-managed PostGIS tables. Offer creation locks the
selected item row, checks the remaining quantity, reserves offered units, and
updates the request status in the same database transaction. A client
submission UUID makes retries idempotent. Optional owner foreign keys connect
signed-in submissions to their account without rejecting guest submissions.
Pick-up adjustments, offer cancellation, and request closure lock the affected
item and recompute request fulfillment transactionally; cancellation cannot
reduce fulfilled units below zero, and closing or owner-cancelling a request
releases all undelivered reservations. Migration 0012 adds account ownership
and the cancelled request state. Migration 0009 adds a shared PostgreSQL token
bucket (up to 120 immediate submissions,
refilling at two per second per endpoint/client address) on public submission
routes. If the browser is offline or the API cannot be reached, an IndexedDB
queue stores the submission and retries it on connectivity restoration and
periodic online checks. Non-retryable 4xx responses are parked as
`needs_attention` rather than retried forever; users may revise the queued
quantity and retry or dismiss the item. Place search uses the existing
configured geocoder with a bounded in-memory cache; the user may instead
explicitly share device coordinates. Open items and inbox offers use PostGIS
`ST_Distance` ordering when the user explicitly supplies coordinates, falling
back to urgency and creation time otherwise. Responder status changes record
UTC timestamps and require an email-verified responder approved by an
administrator. A user's history endpoints filter by the authenticated account
ID; cancellation endpoints verify ownership before changing state. Flag and
close actions store a reason and acting user, and closing releases unfulfilled
offer reservations. The responder badge counts active help requests and offers.

**Inputs and outputs**

- Inputs: consented request/offer details, selected open-item ID, quantity, and
  geocoded or user-approved coordinates.
- Outputs: persisted API records, an IndexedDB retry status when offline,
  remaining-quantity choices, responder workflow state, and EOC aggregates.

**Contribution**

This closes the request-to-offer-to-responder-to-EOC supply-coordination loop.
It is a human-operated coordination capability, not automated matching,
emergency-service dispatch, or a guarantee that a responder is monitoring a
submission.

**Ideas to complete the module next**

- Add an in-app update timeline and notifications when a responder claims,
  contacts, picks up, or delivers an offer.
- Let request owners edit quantities or details before fulfillment begins, with
  transaction-safe checks against offers already reserved.
- Add responder notes and a simple handoff/reassignment workflow for shifts.
- Provide clear cancellation reasons and timestamps in both personal histories
  and responder views, plus a lightweight delivery confirmation from requesters.
- Add duplicate-request hints and a user confirmation step without automatically
  hiding legitimate needs.
- Add pagination and retention controls for long-running request histories.

### 2.7 Operations-center dashboard

The `EOCDashboard` combines database-backed coordination information and
provider/catalogue integrations with clearly bounded static demonstrations.
Its supply-coordination panel fetches live help requests, offers, fulfillment
totals, and responder assignment counts from the backend. The existing map,
some shelter/asset views, and hydrograph remain static or illustrative.

#### Live supply-coordination panel

The panel displays live totals for help requests, open/partially fulfilled
requests, offers, requested/fulfilled units, offers awaiting responders,
assignments, deliveries, and cancellations. It lists recent request quantities
and statuses alongside recent supply offers and pickup/drop locations.
Responders and administrators can flag or close a listed request as spam or a
duplicate; closure releases pending offer reservations. The API requires a
verified, approved responder or administrator because request and offer
records contain contact information.

#### District and layer filtering

The demonstration provides district selection and switches for inundation, shelter, station, SOS, and corridor layers. The filters update the displayed local lists and map-style SVG points.

#### Static shelter view

It includes a shelter list with illustrative names, district, capacity, occupancy, food/medical fields, coordinates, and status. It calculates total capacity, occupancy percentage, and pending/dispatched counts.

These shelter records are presentation fixtures, not verified shelter locations or live occupancy data.

#### Static SOS triage

The view contains illustrative SOS records with priority scores, victim counts, location descriptions, and status. A local Auto-Match function calculates an approximate Euclidean distance in longitude/latitude, selects a nearest static rescue asset, estimates ETA, and changes component state. A Dispatch Team button changes the local status to dispatched.

It does not:

- receive real requests;
- validate or de-duplicate reports;
- contact responders;
- dispatch rescue teams;
- persist results;
- use a real road network or travel-time model.

#### Static hydrograph

The hydrograph tab presents a chart labeled as a 72-hour XGBoost forecast. The values and analysis are hard-coded demonstration constants. The visible text names XGBoost, holdout periods, SHAP, and risk thresholds, but no trained model or live forecast drives the chart.

#### Alert-bulletin preview

The demonstration prepares English, Hindi, and Maithili alert text templates and can use browser speech synthesis when matching voices are installed. It has no publisher workflow, alert authority, approved recipient list, or transmission gateway.

### 2.8 Data-readiness and transparency view

**What it does**

The Data view dynamically queries `/api/v1/status`, live forecast refreshes, and coordinate-local readiness. It distinguishes provider initialization, verified PostGIS shelters, prototype shelter entries, routing, and mock/translated alert availability instead of treating every service as permanently unavailable.

**What it confirms**

It explicitly marks general safety guidance and 112 as available, and it clearly identifies real responder dispatch and live services as not connected.

**Contribution**

The transparency view helps avoid presenting demo data as operational information and provides an audit-friendly explanation of system status.

### 2.9 Authentication, email verification, and roles

**What it does**

The application supports account registration and sign-in with verified email
addresses. Passwords are stored as Argon2 hashes, and the backend issues
short-lived JWT access tokens. Registration defaults to a community account;
the optional responder checkbox creates a pending role request and collects a
responder unit and phone when provided. The account remains a normal community
user until an administrator approves the request. New accounts remain
unverified until the one-time email token is redeemed.

**User workflow**

Users register, inspect the verification message in the local Mailpit inbox,
follow the verification link, then sign in. The sign-in/register view can resend
a verification message for pending accounts. Signed-in users see their account
role and can log out. Responder-only navigation is gated to accounts with the
admin-approved responder flag. The admin dashboard, visible only to admins,
includes responder request review and the account directory. Approval requires
the applicant's email to be verified; rejected users retain normal community
access and can submit a new request.

**Internal behavior**

The `users` table is introduced by an Alembic migration. Email-verification
tokens are stored as SHA-256 digests with expiry timestamps and are consumed on
success. SMTP uses the asynchronous sender configured for Mailpit in Docker
Compose. The frontend stores the bearer token in `localStorage` and resolves
the current account via `/api/v1/auth/me`. Logout increments a per-account
token version so previously issued tokens are rejected by authenticated routes.
Backend dependencies enforce authenticated, verified, responder, and admin
access. Registration cannot set the admin role. A one-time CLI creates the
initial verified admin using an operator-provided username, contact email, and
password and refuses to create another admin once one exists. Admins can sign
in using their username or email; community accounts continue using email.

**Boundaries**

Admin approval is a project-level authorization step, not independent
verification of membership in a real response organization. The supply inbox
is a shared, persisted queue with role-gated assignment and status tracking;
this does not implement SOS matching or real dispatch. Mailpit is a development
SMTP sink, not a production mail provider.
Production deployment requires a secret JWT key, trusted admin credential
handling, suitable email delivery, and security review of token storage and
account recovery.

### 2.9 Backend health endpoint

**What it does**

FastAPI exposes `/health`, which returns `{"status":"ok"}` when the API process is responsive. The root endpoint reports the application name and configured basin name.

**Internal behavior**

The liveness route does not require database connectivity. A separate readiness
route checks database connectivity. Database schema changes are applied
explicitly through Alembic migrations; the API does not create tables at startup.

**Inputs and outputs**

- Input: HTTP request.
- Output: liveness status, database readiness status, or API name/basin metadata.

**Contribution**

It provides a basic deployment liveness check and a first API entry point.

### 2.10 Data audit and flood model preparation

**What it does**

The repository includes real-file auditing, source-aware CSV loaders, feature construction, labels for 24/48/72-hour horizons, baselines, XGBoost training code, metrics evaluation code, chronological data splitting, and unit tests.

**Implemented processing**

- normalizes supported telemetry and discharge headers;
- filters a station by source name and metadata;
- rejects conflicting duplicate measurements;
- creates past-only lag, change, rainfall, upstream, day-of-year, and monsoon features;
- creates future exceedance labels for configured horizons;
- masks incomplete label windows;
- purges training labels that overlap the held-out test period;
- trains an XGBoost classifier for each lead time;
- compares against persistence and optional threshold baselines;
- writes evaluation JSON/Markdown only when a real training output exists.

**Inputs and outputs**

- Inputs: supplied local CSV data and `ml/config.yaml`.
- Outputs: normalized station data, features/labels, saved joblib models when configured, training JSON, and evaluation metrics.

**Real-data status**

The repository has supplied Bihar discharge and telemetry files, but no verified official station ID or danger threshold has been configured. A Birpur daily discharge series is identified as a candidate; Baisi_1 stage telemetry is not confirmed as a Kosi station. Rainfall and upstream data are absent. No real model metrics or trained model is presented as complete.

**Contribution**

This is a reproducible research and data-audit foundation for a future flood forecast. It is not prediction serving or an operational flood warning system.

The platform-wide data inventory at [`docs/data_inventory.md`](docs/data_inventory.md)
records planned and missing data families for the all-hazard application, along
with local file evidence, access/license gaps, and pilot-selection criteria.
It is a repository baseline, not external source authorization or confirmation
that any local file is approved for operational use.

### 2.11 Domain and database scaffolding

SQLAlchemy/GeoAlchemy2 models exist for:

- administrative regions;
- shelters;
- SOS requests;
- volunteer offers;
- help requests and quantity-tracked help-request items;
- supply offers and responder assignments;
- proposed or confirmed SOS/volunteer matches;
- hazard risk scores;
- localized alerts.

These models define geographic points, multipolygon regions, capacity fields, urgency/status fields, and relationships. PostgreSQL/PostGIS is included in Docker Compose, and the initial schema is managed through Alembic migrations.

The supply-coordination API exposes rate-limited public request/offer
submission, responder-only contact-bearing request and offer listings, a
contact-safe open-item listing, transactional supply-offer creation and
cancellation, actual pickup adjustment, ordered assignment/status transitions,
responder/admin spam/duplicate moderation, an active-inbox count, and a
role-protected EOC aggregate endpoint. The help and offer forms are public
submission surfaces; contact-bearing records and moderation actions are
restricted to verified, approved responders and administrators.

The architecture also contains interface placeholders for flood modeling, the common hazard contract, archived-data loading, alert delivery, routing, matching, and Bhashini translation. These are intended extension points, not implemented capabilities.

Read-only `GET /api/regions` and `GET /api/shelters` endpoints expose the
database-backed geographic catalog, including GeoJSON boundary/location
geometries. Shelter records can be filtered by `region_id`; both endpoints
support limit/offset pagination and return empty arrays when no records exist.
Responses include provenance and verification metadata. The offline dataset
intake validates region/shelter GeoJSON against source metadata and can opt into
staging validated features in quarantine tables. `GET /api/datasets` exposes
paginated registry metadata only; the UI presents the registry and its
validation/review/publication state. No public import, verification, review, or
publication write endpoint exists, and staged features are not used by
operational workflows. Rights status is an operator-entered reference, not
legal or source authorization. The broader registry taxonomy does not imply
that hazard, warning, exposure, road, or other data importers exist.

---

## 3. Technical Capabilities

### 3.1 Implemented architecture

| Area | Implemented capability | Boundary |
|---|---|---|
| Frontend | React 18, Vite 7, responsive CSS, dynamic readiness, live coordination clients, and an IndexedDB retry queue for request/offer submissions | PWA shell, offline maps, and cached hazard data are not implemented; other EOC map/asset content remains illustrative |
| Backend | FastAPI liveness/readiness, authenticated role checks, coordination CRUD/workflow APIs, read-only catalogs, provider telemetry, translated mock alerts, shelter lookup, and routing foundation | Telemetry/risk state is in memory; no validated operational model, authoritative alert feed, automated match, or emergency dispatch |
| Database | PostgreSQL/PostGIS, SQLAlchemy models, Alembic schema/provenance/registry/auth/coordination migrations | Manual geography and shelter seed records are unverified; no approved operational dataset |
| Geospatial domain | Region, shelter, help request/item, supply offer/assignment, SOS, volunteer, match, and alert models; geocoded request points | No verified live shelter feed, persisted road graph, or operational closure workflow |
| ML/data | Pandas loaders and feature/label pipeline | No prediction server or trained operational model |
| ML model | XGBoost training and baseline/evaluation code | Cannot train until verified threshold/data inputs are complete |
| Localization | Local English/Hindi cache and approximate country lookup | Bhashini is not integrated |
| Deployment | Docker Compose for frontend, backend, and database | Intended for local development, not production hardening |

### 3.2 Technologies

**Implemented/installed**

- Python 3.11 project convention.
- FastAPI, SQLAlchemy, GeoAlchemy2, psycopg.
- Alembic with an initial PostGIS schema migration.
- PostgreSQL/PostGIS through Docker Compose.
- Pandas and NumPy for tabular data processing.
- XGBoost, scikit-learn, and joblib for training/evaluation in the ML scaffold.
- React 18 and Vite 7 for the frontend.
- Browser APIs for connectivity, geolocation, clipboard, speech synthesis, and sharing.
- pytest and Ruff for tests and linting.

**Partially present in source or configuration**

- Dockerfiles for backend and frontend.
- Environment-based settings for basin name, database, and Bhashini.
- SQLAlchemy spatial model definitions.
- Common hazard interface and flood placeholder.
- Alert and translation placeholder modules.

**Not yet implemented despite project plans**

- Write-capable SOS, volunteer, alert, and forecast APIs.
- Persisted APScheduler replay, anomaly history, or scheduled risk storage.
- MapLibre/Leaflet mapping.
- PWA service workers and IndexedDB.
- i18next integration.
- OSMnx/NetworkX routing.
- Persisted APScheduler/httpx operational ingestion.
- Approved Bhashini ULCA/Dhruva request execution.
- Real paid SMS or broadcast delivery.

### 3.3 Data processing and storage

The frontend stores state only in memory. It does not persist submitted forms or coordinates. Its operations-center Database Catalog tab fetches read-only region and shelter records from the backend API and displays their verification/provenance metadata; current database records default to unverified prototype status and remain distinct from the static shelter demonstration. Vite proxies local `/api` requests to the configured backend.

The backend has a SQLAlchemy engine with a pool and session dependency. The
configured PostgreSQL instance uses PostGIS and a persistent Docker volume.
Alembic migrations define the initial schema and geography provenance fields
and are run explicitly; there is no automatic schema creation or seeding at
API startup, and no API currently manages the domain models. An optional manual
seed script includes prototype geography labeled as unverified.
Region and shelter rows carry a source name, optional reference/license, and verification state.
The migration marks existing rows `unverified`; imports are not yet persisted,
and validated import schemas cannot set verification status. Verified records
require reviewer/time evidence, but the status is not a live safety guarantee.

The ML pipeline reads local CSV files, normalizes known source schemas, creates a station-centric table, applies no-future feature construction, removes future contamination, and writes models/evaluation artifacts when real training is valid.

### 3.4 APIs and communication

The implemented endpoints are `/health` for liveness, `/ready` for database
connectivity, read-only `/api/regions`, `/api/shelters`, and `/api/datasets`
catalog routes, on-demand `/api/telemetry/sentinels` open-provider ingestion,
and V1 live forecast, alert, shelter, routing, and status routes. The V1 alert
route supports Bhashini/deep-translator/local fallback and mock dispatch. Write
operations and persisted SOS, alert, and risk domain APIs remain limited.
Browser services communicate directly with the browser rather than the backend
for sharing, clipboard, geolocation, and speech synthesis.

### 3.5 AI/ML capabilities

**Implemented in code**

- Past-only feature engineering.
- Chronological 2022–2023 training and 2024–2025 test configuration.
- 72-hour purge to avoid label-window overlap.
- XGBoost binary classification for 24/48/72-hour threshold exceedance.
- Persistence and optional threshold-rule baselines.
- Precision, recall/POD, false-alarm ratio, F1, and Brier-related evaluation support in the evaluation module.

**Not implemented**

- A real calibrated model.
- Model serving.
- SHAP explanation output from a real trained model.
- Real flood probability results.
- Regional/ward-level risk prediction.
- Continuous discharge regression.
- Multi-hazard models.

The XGBoost model names and SHAP numbers visible in the operations-center UI are demo presentation, not actual experimental results.

### 3.6 Automation and optimization

The only implemented intelligent behavior is the data pipeline and local-time distance ranking in the operations-center demo. The project also defines interfaces for hazard-specific future modules, but they do not contain operational decision logic.

There is no production optimization system, route optimization, demand matching, duplicate detection, misinformation screening, or alert automation.

---

## 4. Practical Applications and Use Cases

### 4.1 General community preparedness

A community member can open the app to review 14 general hazard categories, prepare a household checklist, understand emergency actions, and save or dial national emergency numbers.

**Limitation:** guidance is general and must be supplemented with official local instructions.

### 4.2 Household disaster planning

A family can use the Before section to plan meetings, essential supplies, medicines, documents, communication, and trusted information sources.

**Limitation:** there is no household profile, saved plan, reminder system, or household data persistence.

### 4.3 Location-assisted safety reference

During a hazard, a user can obtain and manually share coordinates. This may help if the user then chooses to provide them to trusted people or official responders.

**Limitation:** coordinates are not sent to any monitored SOS system.

### 4.4 Safety-guide demonstration for education

In a classroom or training session, participants can compare phase-specific actions for floods, earthquakes, heatwaves, storms, and industrial incidents.

**Limitation:** the guides are not jurisdiction-specific operational instructions and may not cover all local protocols.

### 4.5 Local form and matching concept demonstration

An administrator or evaluator can demonstrate a request/offer form and the conceptual needs/capacity matching workflow. The operations-center mock also shows local triage and nearest-responder ranking.

**Limitation:** all request and dispatch results are in-browser demo state only.

### 4.6 Flood data development workflow

A data analyst can audit supplied files, normalize station schemas, create no-future features and labels, and run chronological tests. Once thresholds and additional data are verified, the same code can train and evaluate a candidate model.

**Limitation:** no real trained model is currently usable for forecasts.

### 4.7 Project evaluation and academic demonstration

The repository is suitable for architecture explanation, data-engineering review, ML methodology evaluation, UI demonstration, Docker-oriented setup, and viva preparation.

**Limitation:** evaluators should clearly identify static mock views and research scaffolding so that demonstrations are not interpreted as live emergency capability.

---

## 5. Current Limitations and Constraints

### 5.1 Functional limitations

- Forecasting, alerting, routing, and emergency dispatch are not operational services.
- Help requests and supply offers persist; separate SOS and volunteer endpoints/workflows remain unimplemented.
- Operations-center coordination metrics/records are database-backed, while some shelter, SOS, rescue, map, and hydrograph records remain demonstrations.
- There is no real flood risk API or trained model endpoint.
- The common HazardModule interface is a contract, not a working multi-hazard engine.
- There is no alert queue, message approval, recipient management, or delivery report.
- No approved live shelter feed or official road/routing dataset is connected; prototype catalogue and cached road graphs are not authoritative.
- Help/supply domain APIs exist; CRUD for other domain models such as SOS reports, shelter operations, and matches is not implemented.

### 5.2 Technical and infrastructure limitations

- The backend does not yet expose routes for SOS, volunteers, matches, alerts, or forecast scores.
- Docker Compose is a local-development scaffold and lacks production secret management, TLS, scaling, observability, and backup policies.
- Coordination records persist in the backend, and pending submissions use IndexedDB. Other frontend state is not persisted between reloads.
- No PWA service worker or offline map/data cache exists.
- Database schema changes require explicitly running Alembic migrations.
- The help/supply and selected data/readiness workflows call FastAPI; some EOC panels remain illustrative.
- Authentication and role authorization are implemented for the current prototype, but production security hardening remains necessary.

### 5.3 Data availability and quality

- Supplied discharge and telemetry provenance is not fully documented.
- The official Birpur station ID is unknown.
- Birpur's verified danger threshold and source are unknown.
- Baisi_1 is not confirmed as a Kosi station.
- Rainfall, upstream discharge, DEM, boundaries, flood extents, and official shelter files are unavailable or unspecified.
- 2025 holdout data ends in May, so the planned test period is not a complete multi-season monsoon assessment.
- Historical telemetry and discharge ranges include gaps and irregular metadata.

### 5.4 Accuracy and reliability

- Safety guides are general guidance and should not replace official local advice.
- No real model accuracy metrics are available.
- Static hydrograph values and SHAP-style explanations are not generated by a trained model.
- Distance matching uses longitude/latitude Euclidean approximations, not road distances or travel times.
- Location and country-language detection are approximate.
- Browser connectivity status indicates network availability, not application service availability.

### 5.5 Scalability

The current UI can scale as a static site, and the coordination schema includes PostGIS GIST indexes and distance ordering. The repository does not yet demonstrate horizontal API scaling, load balancing, queue-based alert dispatch, or model-serving throughput.

### 5.6 Security and privacy

- The current form and coordinate behaviors are intentionally local and reduce transmitted personal data, but production systems would require explicit privacy controls.
- Default database credentials are local-development values and must be changed.
- Email verification, approved responder/admin role checks, request validation, and a shared rate limiter for the two public coordination submission endpoints are implemented. A general-purpose audit log, broader API abuse controls, and production privacy/retention safeguards are not.
- SOS and medical details could become sensitive in a real deployment, requiring encryption, retention policies, access control, consent, and abuse controls.
- Static contact numbers should be validated for local coverage before production use.

### 5.7 External dependencies

- Bhashini is optional and not configured.
- Real SMS or cell-broadcast providers are out of scope.
- Official gauge, rainfall, weather, geographic, shelter, and road data remain unverified or unavailable.
- Docker Desktop is needed for the complete local stack.

---

## 6. Realistic Future Scope

### Short-Term Enhancements

| Enhancement | Value | Potential implementation | Dependencies | Challenges | Feasibility |
|---|---|---|---|---|---|
| Expand FastAPI endpoints for SOS, alerts, and scores | Turns remaining scaffolds into usable services | Pydantic schemas, SQLAlchemy dependencies, CRUD and status endpoints | Stable API contracts and authentication decisions | Input validation and human review | High |
| Exercise migration upgrades and existing-database adoption in CI | Keeps schema evolution reproducible | Test Alembic upgrades and schema checks against disposable PostGIS databases | PostgreSQL/PostGIS test service | Extension-managed schema objects | High |
| Replace demo EOC lists with API-backed state | Converts static UI into a coherent prototype | Seed/read domain models and add React API hooks | CRUD APIs and local seed data | Keeping demo data clearly labeled until verified | High |
| Complete flood model threshold configuration | Enables valid real model training | Add verified station ID, danger level, units, source/effective date | Authoritative station documentation | Data and license provenance | High, subject to information availability |
| Add rainfall and upstream discharge inputs | Improves flood feature coverage | Place approved local archives in `ml/data/raw` and set metadata | Verified rainfall/upstream files | Spatial/temporal alignment and rights | Medium-high |
| Expand API and database integration tests | Improves confidence and maintainability | TestClient routes, disposable PostGIS fixtures, loader edge cases | Test database setup | CI environment for PostGIS | High |
| Add verified real shelter data | Supports useful shelter information | Import approved boundary/shelter records and expose read-only endpoints | Vetting, licenses, and coordinates | Liability and freshness | Medium-high |
| Improve localization coverage | Makes existing interface more accessible | Replace cache-only strings with structured resource files | Hindi and regional review | Translation quality and terminology | High |
| Implement local PWA caching for guides | Allows preparedness guidance during network loss | Service worker, app-shell cache, static safety JSON | Clear update/version strategy | Cache invalidation and stale medical guidance | Medium-high |

### Medium-Term Enhancements

| Enhancement | Value | Potential implementation | Dependencies | Challenges | Feasibility |
|---|---|---|---|---|---|
| Deploy a flood prediction API | Makes trained forecast output available to applications | Load joblib model in a versioned FastAPI service; expose probability and lead time | Real model metrics and calibrated thresholds | Model drift and operational validation | Medium |
| Add archived-data replay | Supports safe scenario demonstrations | APScheduler or an explicit replay endpoint reads timestamped archive inputs | Verified historical datasets | Reproducibility and replay speed | Medium |
| Integrate a base map | Improves spatial understanding | Leaflet or MapLibre with static verified layers | Boundary and point data | Offline tiles and attribution | Medium-high |
| Add OSM-based routing | Can suggest road paths to verified shelters | osmnx/networkx or a hosted routing service | Verified road extract and shelter points | Flood closure handling and route trust | Medium |
| Implement human-confirmed SOS matching | Connects need and capacity responsibly | Location, need type, urgency, status, audit trail, and confirmation | Authentication and abuse controls | Privacy, false reports, duplicate requests | Medium |
| Build a mock alert gateway | Tests alert preparation and delivery workflow safely | Queue, template, recipient, and delivery-status records | Approved mock provider | Avoid accidental real dispatch | Medium-high |
| Integrate a configured Bhashini client | Enables approved translation workflows | Implement exact provider contract and fallback | Credentials and pipeline endpoints | Provider contract, cost, and fallback behavior | Medium |
| Add regional administrative boundaries | Supports ward/district risk and incident views | Import licensed GeoPackage/Shapefiles | Official boundary vintage | Attribution and boundary disputes | Medium |
| Add model monitoring and retraining workflow | Keeps flood predictions relevant | Data drift, validation windows, run registry, scheduled retraining | Historical and continuous approved data | Small sample size and concept drift | Medium |

### Long-Term Possibilities

| Enhancement | Value | Potential implementation | Dependencies | Challenges | Feasibility |
|---|---|---|---|---|---|
| Production multi-hazard risk platform | Expands beyond flood pilot across hazards | Implement each hazard behind HazardModule; combine regional services | Valid hazard data and expert review | Certification, false-alarm costs, multi-source inconsistency | Medium-low |
| Ward-level ensemble forecasting | Provides more local flood risk information | Station and gridded rainfall, DEM, inundation extent, calibrated ensemble models | Extensive verified spatial data | Uncertainty quantification and limited observations | Medium-low |
| Hazard-aware evacuation optimization | Improves shelter routing | Dynamic road weights, closures, capacity, crowd estimates | Live/authoritative road and shelter feeds | Liability and real-time reliability | Medium-low |
| Offline-first field operations | Enables low-bandwidth response use | PWA caching, IndexedDB queues, signed synchronization | Conflict and security design | Data reconciliation and stale local information | Medium-low |
| Governed Bhashini and regional-language expansion | Better access for pan-India users | Approved translation pipelines, human review, terminology standards | Provider access and language expertise | Quality, consent, and operational cost | Medium |
| Real-time monitored alerting | Supports recognized emergency communication channels | Authorized gateways, templates, geofencing, recipient consent | Public authority partnerships | Legal, operational, and safety risks | Low without institutional mandate |
| Integrated SOS, volunteer, and response operations | Creates a complete community response platform | End-to-end APIs, role-based workflows, audit trails, dispatch confirmation | Trained operators and governance | Abuse, privacy, scale, and accountability | Low to medium, requires partnerships |

---

## 7. Potential Integrations and Expansion

### Approved archived datasets

- **IMD:** daily rainfall and weather inputs, only through supplied/licensed archives; no restricted portal scraping.
- **CWC or India-WRIS:** river stage/discharge observations, subject to confirmed station IDs and licensing.
- **ISRO MOSDAC/Bhuvan:** flood-extent and geospatial products for replay and validation.
- **OpenStreetMap:** road and shelter data, subject to ODbL attribution/share-alike requirements.
- **Administrative boundaries:** official district/block/Gram Panchayat/ward sources with documented vintage and usage rights.

### Translation and accessibility

A configured Bhashini pipeline can be used for approved translation. It should be coupled with local fallback, language labeling, and human review of safety-critical phrases. The local cache should remain as a resilience mechanism when the service is unavailable.

### Mapping and routing

Leaflet or MapLibre can use static or cloud-hosted tiles, while OSMnx/NetworkX or a separate routing engine can use local road extracts. Routing should remain independent of any specific hazard; a hazard module should provide edge closures or risk weights rather than embedding flood logic in core route code.

### Complementary systems

- district administration and disaster-management dashboards;
- hospitals and health-service directories;
- NDRF/SDRF or state rescue command systems, only through authorized integrations;
- public radio or broadcast content-management systems;
- shelter-management platforms;
- weather and hydrology monitoring systems.

These integrations should follow formal data-sharing agreements and human-approval workflows before production dispatch or emergency use.

### Cloud and deployment

A production deployment could use PostgreSQL/PostGIS, object storage for approved datasets and model artifacts, a container platform, managed secrets, HTTPS, centralized logs, and metrics. Automated CI should run Python tests, frontend builds, SQL migrations, and data pipeline validation.

Cloud infrastructure should be introduced only after privacy, data provenance, backup, and role requirements are defined.

### Additional AI/ML

Useful additions would include probabilistic calibration, uncertainty intervals, model drift monitoring, rainfall-driven nowcasting, spatial interpolation, and validated ensemble models. Generic “AI” features should not be introduced unless they improve one of the application's defined disaster-lifecycle objectives.

---

## 8. Roadmap for Future Development

### Phase 1 — Stabilize and connect the scaffold

**Priority:** high  |  **Complexity:** low–medium  |  **Primary benefit:** usable and testable foundations

1. Keep the Alembic baseline workflow tested for fresh and existing local
   databases.
2. Expand the read-only region/shelter catalog API, then add domain APIs for
   response workflows.
3. Introduce authentication and role concepts only where needed.
4. Replace static operations-center core records with API-backed verified or explicitly labeled demo records.
5. Add API, loader, and frontend build tests to CI.

### Phase 2 — Complete data and geospatial foundations

**Priority:** high  |  **Complexity:** medium  |  **Primary benefit:** trustworthy local decisions

1. Verify Birpur's official station ID and danger threshold.
2. Document the provenance and licensing of all supplied data.
3. Acquire approved rainfall, upstream discharge, and boundary datasets.
4. Import verified shelters and map boundaries.
5. Add an inspectable data-quality and lineage screen.

### Phase 3 — Deliver a real flood prototype

**Priority:** high  |  **Complexity:** medium  |  **Primary benefit:** evidence-based 24/48/72-hour forecasting

1. Re-run chronological training with complete, legitimate data.
2. Publish versioned metrics and calibration results.
3. Compare XGBoost with persistence and operational baselines.
4. Add a flood prediction endpoint and UI uncertainty information.
5. Keep all forecasts clearly labeled and non-authoritative until validated.

### Phase 4 — Implement safe response workflows

**Priority:** medium  |  **Complexity:** medium-high  |  **Primary benefit:** demand and capacity coordination

1. Implement local SOS and volunteer APIs.
2. Add duplicate detection, human confirmation, status tracking, and audit records.
3. Add map and road-aware matching.
4. Build a mock alert gateway and approved template workflow.
5. Integrate verified shelters and closures.

### Phase 5 — Expand and harden

**Priority:** medium  |  **Complexity:** high  |  **Primary benefit:** sustainable multi-hazard use

1. Implement additional HazardModule classes using validated data.
2. Add PWA/offline caching and signed synchronization.
3. Expand approved regional-language support.
4. Add model monitoring, role-based access, encryption, and operational observability.
5. Pursue authorized institutional integrations and independent validation.

### Recommended near-term sequence

The platform-wide sequence is:

1. **Complete:** inventory all data families and record local evidence,
   authorization gaps, and candidate-pilot criteria in `docs/data_inventory.md`.
2. Define shared provenance, freshness, quality, and review contracts without
   forcing hazard-specific inputs into a flood schema.
3. Build controlled, traceable ingestion after an authorized dataset and its
   terms are confirmed.
4. Make provenance, coverage, review state, and freshness visible in the
   catalog while keeping prototype content distinct.
5. Deliver one end-to-end, approved real-data pilot; the local flood archive is
   only a candidate pending source and permission confirmation.
6. Reuse shared ingestion foundations for other hazard and data families.
7. Design privacy and access controls before connecting SOS and volunteer
   submissions or human-reviewed matching.
8. Add predictions, routing, and mock alerts only when their inputs and safety
   behavior are validated.
9. Harden and broaden the platform with CI, monitoring, backups, localization,
   offline support, and additional hazards.

This sequence prioritizes correctness and trust over feature volume.

---

## 9. Conclusion

AapdaSetu currently provides an accessible multi-hazard readiness interface and an initial flood-data and software-engineering prototype. It includes 14 hazard categories, structured Before/During/After safety information, English and limited Hindi fallback behavior, user-controlled location sharing, persistent help and supply coordination with IndexedDB retry triage, row-locked quantity reservation/rollback, responder assignment and actual-pickup tracking, approved-role authorization, request moderation, shared submission throttling, PostGIS distance ordering, live EOC coordination aggregates, a data-readiness page, and Docker-based backend/frontend scaffolding.

It also provides a well-separated technical foundation for regional models, spatial records, SOS and volunteer concepts, alerts, hazard modules, and flood training. Realized ML support includes past-only feature engineering, chronological splitting, labeled unit-test fixtures, XGBoost training code, and evaluation infrastructure.

Its present boundaries are equally clear. Authoritative warnings, validated predictions, shelter import and verification workflows, operational routes, SOS matching, emergency dispatch, translation services, PWA/offline map caching, and real model metrics are not implemented. The supply-coordination workflow records human-submitted information; it does not certify needs, guarantee monitoring, or contact emergency services. Read-only catalog endpoints return database records but source labels and review status do not provide an operational safety guarantee. Some records and numbers visible in the operations-center interface remain illustrative. The supplied data requires provenance, station, threshold, and additional dataset work before operational training.

AapdaSetu's realistic future value lies not in adding unsupervised or generic AI features, but in building a verified, migration-based, API-backed platform: trustworthy datasets first, real tested flood risk second, human-controlled response and alert workflows next, and then broader hazard and regional expansion. With those constraints and dependencies respected, the application can evolve from a concept and academic prototype into a useful decision-support and community-resilience platform.

---

## Implementation Status Summary

| Status | Existing examples |
|---|---|
| Implemented | React navigation and hazard guides, local language fallback, location sharing, persistent PostGIS help requests/items/supply offers/assignments, account-scoped request and donation histories, owner cancellation of active requests and undelivered offers, transactional quantity fulfillment/cancellation/pickup adjustment, IndexedDB retry plus needs-attention handling, role-gated responder queue of help requests and offers with claims/status updates, request spam/duplicate moderation, database-shared public submission rate limits, PostGIS distance sorting, live EOC coordination metrics/records, email-verified authentication and admin-approved responder roles, backend health/readiness and catalog APIs, Alembic coordination migrations, quarantined geography intake, data inventory/audit/loaders, flood feature/label tests, Docker Compose |
| Partially implemented | SQLAlchemy/PostGIS setup, Bhashini configuration, database migration workflow, flood training/evaluation, operations-center UI, dataset source review and publication workflow |
| Demonstration only | Shelter/SOS/asset lists, hydrograph, SHAP labels, distance matching, dispatch state, alert bulletin |
| Prototype available | Open-provider telemetry polling, prototype flood risk payloads, V1 translated/mock alert delivery, Pan-India shelter lookup, OSMnx/NetworkX routing fallback, and service status |
| Remaining boundaries | Authoritative forecasts/alerts, persisted telemetry/risk, verified shelter and road data, real matching, PWA, approved Bhashini execution, write-capable SOS APIs, model serving, and real dispatch |

## Repository Evidence Reviewed

- The platform-wide data inventory was cross-checked against project context,
  configuration, models, seed/demo code, and frontend behavior.
- The local raw-file audit was regenerated on **2026-11-19**.
- The inventory does not claim that external permissions were independently
  confirmed or that any dataset is cleared for operational use.
- No real model metrics or trained model artifacts were treated as existing.
