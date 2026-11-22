# AapdaSetu project context

## Vision

AapdaSetu is a data-driven disaster-management platform built around
**"Swadeshi for Aatmanirbhar Bharat"**: Indian data sources and regional-language
support should make useful disaster information accessible before, during, and
after an emergency.

## Disaster lifecycle

- **Before:** estimate hazard risk at local administrative-area level and
  prepare localized alerts.
- **During:** guide people toward safer shelters using hazard-aware routes and
  concise safety guidance, including an offline/low-bandwidth experience.
- **After:** collect victim SOS/needs and volunteer capacity, then match them
  using distance, need type, and urgency while filtering duplicates and likely
  fake requests.

These are product goals, not claims that the current scaffold implements these
features. Real SMS/cell broadcast is out of scope; alert delivery will use a
mock gateway.

## Prototype scope and extensibility

- AapdaSetu's **project vision is multi-hazard and pan-India**. The first
  working data/model prototype is deliberately limited to **riverine flood**;
  that prototype boundary is not the scope of the whole platform.
- The pilot is the **Lower Kosi Sub-Basin, North Bihar**, with `BASIN_NAME`
  configurable. Its four focus districts are Supaul, Saharsa, Madhepura, and
  Purnia, modeled at district/block/Gram Panchayat/ward polygon level.
- Primary checkpoint names are Birpur Barrage upstream and Baltara/Kursela
  downstream.
- The architecture provides a common `HazardModule` interface. Cyclone,
  landslide, drought, and heatwave modules are future extensions; adding them
  must not require hazard-specific changes to core routing, alerts, or SOS
  matching.
- Archived IMD rainfall, CWC gauge/discharge, ISRO MOSDAC/Bhuvan flood extent,
  and OpenStreetMap road/shelter data are intended as replay inputs. No
  restricted portal scraping, live sensor hardware, or live satellite tasking
  is planned. Source URLs and formats are intentionally not guessed; loader
  interfaces and TODOs mark the integration points.
- Planned regional-language support uses Bhashini with a local fallback cache.
  The provider client is not configured; uncached UI and safety text stays in
  English.
- Planned offline PWA support includes cached risk maps, shelter coordinates,
  and precomputed evacuation routes; those capabilities are not implemented.
  Supply-coordination form submissions have a separate IndexedDB retry queue.

## Technology stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy, GeoAlchemy2, PostgreSQL/PostGIS,
  Alembic, APScheduler, async SMTP via Mailpit in local development, Argon2
  password hashing, JWT access tokens, and httpx for the Bhashini wrapper.
- **ML/data:** pandas, scikit-learn, XGBoost, joblib, geopandas, rasterio, and
  xarray.
- **Routing:** osmnx and networkx, with hazard-weighted edges and A* planned.
- **Frontend:** React, Vite, MapLibre GL or Leaflet, PWA/service worker,
  IndexedDB, i18next, and Bhashini localization.
- **Infrastructure and quality:** Docker Compose, `.env` configuration, pytest,
  and Ruff.

Only the dependencies needed by the current scaffold are installed. Add the
remaining stack dependencies as their corresponding features are implemented.

## Folder responsibilities

- `.github/`: repository instructions for Copilot; this file points to this
  canonical context.
- `backend/app/api/`: HTTP routes; `core/`: configuration and DB setup;
  `models/`: SQLAlchemy/PostGIS tables; `schemas/`: API request/response types.
- `backend/app/hazards/`: common hazard contract and individual modules;
  `routing/`, `matching/`, `alerts/`, and `bhasini/`: isolated domain services;
  `services/`: shared service interfaces such as archived-data loading.
- `backend/tests/`: backend tests.
- `ml/notebooks/`: exploratory work; `ml/data/raw/` and `processed/`: local
  dataset locations; `ml/training/` and `evaluation/`: model workflows.
- `frontend/src/components/`, `pages/`, `i18n/`, `offline/`, `api/`, and
  `bhasini/`: reusable UI, views, localization, offline behavior, API access,
  and language-service integration.
- `docs/`: project documentation and design notes.

## Coding conventions

- Use Python 3.11 type annotations and small, explicit modules.
- Prefer clear names and concise comments that explain non-obvious decisions.
- Keep data-source URLs, credentials, and deployment secrets out of source.
- Surface incomplete integrations as explicit TODOs or errors; do not return
  fake successful data.
- Keep hazard-specific rules inside a `HazardModule` implementation.
- Test behavior that is already implemented, and update this context when
  architecture or implementation status materially changes.

## Current implementation status

**Backend core services and live-provider foundation are active.** The repository
contains FastAPI liveness and database-readiness endpoints, environment-based
configuration, a SQLAlchemy engine configured for PostGIS, Alembic migrations
for the initial spatial domain schema, initial domain models, a
read-only regions and shelters API returning GeoJSON geometries,
async Open-Meteo Flood/Weather/Elevation and GDACS provider adapters with a
configurable sentinel grid and `/api/telemetry/sentinels` foundation endpoint,
`HazardModule` contract and `FloodModule` implementation foundation, live telemetry
status and coordinate-readiness V1 endpoints, a Bhashini fallback chain, basic
Docker Compose services, a React/Vite shell, and backend tests. Database schema
changes are applied explicitly with Alembic and are not created at API startup.

Milestone 1 of the platform-wide real-data plan is complete as a repository
baseline: `docs/data_inventory.md` inventories geography/exposure, hazards,
warnings, response resources, roads, user submissions, and guidance/localization.
It records the currently present local flood files and evidence gaps. No
external data source or license has been approved by this inventory, and no
dataset is cleared for operational use. The flood files' source attribution
remains unverified.

Region and shelter rows include a source name, optional reference/license, and
an explicit verification status. Existing records migrate as `unverified`;
verified rows require a reviewer and timezone-aware timestamp. Milestones 2-4
of the platform-wide data plan now provide shared dataset/evidence metadata,
an offline GeoJSON validator and opt-in quarantined staging CLI for regions and
shelters, and a paginated read-only dataset registry API/catalog. The importer
does not write operational region/shelter tables, and no review, publication,
or verification write API exists. Open telemetry is on-demand adapter
foundation only: APScheduler polling, persistent ingestion, anomaly detection,
and risk storage are not implemented. External open-provider responses are not
authoritative observations or live operational warnings. Registry rights status is operator-supplied
documentation, not legal clearance. No dataset is approved for operational
use; Milestone 5 (an authorized real-data pilot) remains paused.

Authentication foundations now include UUID user accounts, Argon2 password
hashing, expiring one-time email-verification tokens, async SMTP delivery,
JWT-backed sign-in with token-version invalidation on logout, and
verified-user/responder/admin dependencies. A responder
checkbox creates a pending role request only; users remain community accounts
until an email-verified account is approved by an administrator. Admins can
review and approve/reject requests, and a rejected user can request again.
Administrators are provisioned with a one-time CLI using operator-selected
credentials in local environment configuration. Bootstrapped admins can sign in
with their unique username or email; email is also their contact/verification
address.
Regular accounts sign in with email. Registration cannot grant the admin role.
Mailpit is included in local Compose for verification-email testing.
Responder authorization is not independent organizational validation. The
persistent supply-coordination queue supports human assignment and delivery
status tracking, but it does not dispatch emergency services.
Authenticated users can maintain an optional contact phone and usual address
in profile settings. Help-request forms prefill the account name, phone, and
saved address, and supply-offer forms prefill name and phone; these values
remain editable and each submitted coordination record keeps its own contact
details. The saved address is not treated as the user's current incident
location: help requests still require explicit location selection.

The flood data-modelling scaffold includes a data inventory, real-file audit,
typed loaders for the supplied multi-station Bihar telemetry and daily
discharge CSV schemas, no-future features and 24/48/72-hour labels, baselines,
per-station XGBoost training, metrics, and two notebooks. Local files include a
daily Birpur Barrage/Kosi discharge series and Bihar water-level telemetry.
Birpur's official station ID and danger discharge level remain unverified.
A chronological year split is configured for train 2022-2023 and test
2024-2025 with a 72-hour pre-test label-window purge. The test period contains
only one complete monsoon season because 2025 observations stop in May.
Telemetry for Baisi_1 has no river or basin attribution and is not an active
Kosi training target. No real model metrics have been generated, and synthetic
observations are used only in labelled unit-test fixtures. The repository now
has prototype live-provider ingestion, flood risk payload generation, translated
alert/mock-dispatch endpoints, Pan-India shelter catalogue lookup, and
NetworkX/OSMnx routing foundation, plus place/district geocoding through configured Google Maps or an OpenStreetMap/Nominatim fallback. It does not yet provide validated real flood
prediction, authoritative alerts, persisted geospatial routing, SOS matching,
or PWA offline storage.

The frontend presents AapdaSetu as an all-India, multi-hazard platform with
interactive cards for 14 natural and human-made hazard categories and
hazard-specific safety guidance loaded from the database for before, during,
and after an event. Existing baseline guidance is seeded as published records
and is managed through the Admin safety-tip library; guidance content is not
hardcoded in the frontend.
Selecting “View safety guide” on a hazard card expands a compact phase table
and relevant emergency contacts directly inside that card; overview hazard
cards link directly to the matching expanded guide.
English is the default interface language. Device location filters the
language selector using a local approximate country-level lookup; a manual
override remains available. Bhashini credentials are not configured, so local
cached translations are used where present and uncached safety text stays in
English. Hazard guides include emergency, ambulance, and relevant fire-service
contacts; local availability can vary, and 112 is the fallback. Users can
explicitly request device location during a disaster and share or copy it; the
app does not automatically transmit or persist coordinates. The UI also
includes a session-only SOS/volunteer demonstration form that places submissions
in an in-app responder inbox with editable demonstration statuses. Submissions
are held only in browser memory, disappear on reload, and are not transmitted to
real responders or emergency services; no SOS persistence, matching, or live
dispatch integration is implemented. Separately, the Get or offer help view
persists structured help requests, quantity-tracked items, supply offers, and
responder assignments through FastAPI and PostGIS. Help requests are geocoded
through the place-search service or user-approved device coordinates; submitted
requests include an SRID 4326 point. Offers reserve remaining quantities in a
row-locked transaction and update request fulfillment status. Migration 0009
adds responder/admin offer cancellation, actual picked-up quantities, request
moderation, and a PostgreSQL-shared token-bucket limit for public submissions
(120-request burst, refilling at two requests/second per endpoint and client
address). Cancellation and moderated closure lock request items and release
reservations; only delivered quantities remain fulfilled after closure.
Picked-up quantities may be adjusted from zero through the pledged quantity,
with parent request status recalculated in the same transaction. Open items,
responder help requests, and responder offers sort by PostGIS `ST_Distance`
when an explicitly provided location is available, then by urgency and
creation time; otherwise they use urgency and creation time. When the API is
offline or unreachable, submissions
are stored in IndexedDB and retried automatically; idempotency keys protect
retries against duplicate records. Non-retryable 4xx sync conflicts are parked
as `needs_attention` and can be edited by quantity or dismissed by the user.
Only email-verified responder accounts approved by an administrator can access
the inbox, which presents active help requests and their donor offers in one
table. Requester details are shown as soon as a request arrives; donor and
pickup fields indicate when no offer has been made yet.
Migration 0012 associates submissions made while signed in with their account;
authenticated users can review request/offer history after reload and across
sessions, cancel their own active requests, and cancel their own undelivered
offers. Guest submissions remain accepted but are not attached to an account.
Assigned responders and administrators can also cancel offers, while
responders/administrators can flag or close spam/duplicate requests. The
responder badge counts active requests and offers. The EOC dashboard reads live
coordination metrics and records. This is a
human-coordinated workflow, not an emergency service or automated dispatch.
The EOC view also loads provider risk snapshots, shelter catalogue records, and
persisted SOS records on entry or operator refresh. Its summary distinguishes
prototype risk indicators and recorded occupancy from verified live operational
status; it does not treat missing people counts or responder inventory as zero.
The map is a schematic coordinate plot of returned records, not a basemap or
navigation display. Static evacuation corridors and simulated responder
matching/dispatch are not presented as live operations. The EOC includes
record filters, linked map/detail inspection, review cues, and a printable
snapshot brief.

Migration 0010 adds an operator-managed incident registry with hazard, affected
area, lifecycle status, and actor timestamps. Administrators create/close
incidents; verified responders or administrators can link catalogue shelters
to an incident and publish status/occupancy updates. Incident occupancy is
kept separate from the reusable shelter catalogue, update actors and timestamps
are recorded, and occupancy cannot exceed a shelter's registered capacity.
Community members can submit a geolocated, idempotent and rate-limited SOS,
optionally linked to an active incident; the location is requested only after
the user presses the location button. Responders/administrators can acknowledge
or resolve incident-linked SOS records. The incident selector scopes the SOS,
shelter metrics and schematic map; the dashboard refreshes these operational
records every 15 seconds and displays the last fetch/update time.

These are near-live citizen/operator submissions, not external live sensor or
government feeds. A shelter must be deliberately linked by an operator and its
status/occupancy is not independently verified. Incident areas are labels, not
validated boundaries. Live road closures, rescue/shelter navigation, routes,
provider-to-incident association, historical playback, simulation event
generation, incident timeline, responder location/capacity, automated
matching/dispatch, and official alert dispatch remain unimplemented. Super
Administrators can manage isolated simulation scenario metadata, but those
records do not affect live incidents, SOS requests, alerts, or response
services. Provider forecasts remain
separate prototype flood indicators and are excluded from an incident's map.
The application is not an emergency service.
Login and registration screens require email verification, persist JWT access
tokens in browser local storage, and show signed-in account details and logout.
Responder navigation is role-gated, and verified administrators can inspect the
account directory and decide pending responder-role requests. The Admin page
also provides soft account deletion/restoration, a searchable account directory,
published-draft safety-tip management, and incident/SOS moderation views.
Existing phase-by-phase guidance for all 14 hazard categories is seeded as
published database records. Safety tips are stored with hazard, lifecycle phase,
language and status metadata; the public guide and Admin library read the
database, and the public API exposes only published tips. The bootstrap account is assigned
Super Administrator status; only that role can promote verified normal accounts
to Administrator or demote regular Administrators. Other normal-user account
actions and safety-tip management remain available to Administrators.
Only Super Administrators can start or stop one isolated simulation scenario at
a time and view the recent privileged-action audit log. Simulation management
stores scenario metadata only; generated events and live-dashboard projections
are not implemented. Account, role, responder-approval, safety-tip, incident,
and simulation mutations are recorded in the audit log.
Administrator
roles must be provisioned by a trusted operator. The responder inbox is a
shared, persistent queue of active help requests and supply offers, restricted
to verified responders and administrators; it supports offer claims and ordered
delivery status updates. Signed-in submissions appear in account-specific
request and offer histories, where owners can check status and cancel active
requests or undelivered offers. Guest submissions remain available but are not
linked to account history. Its
operations-center Database Catalog tab fetches region and shelter records
from the backend and clearly separates them from static shelter demonstrations.
Catalog records display provenance and verification status; they are not
represented as operational until explicitly associated with an incident and
updated by an operator. The optional local seed script labels its prototype
geography as unverified. Provider risk snapshots are available but do not
constitute validated flood predictions or active incident records. Shelter
import/verification workflows, navigation routing, official alert dispatch,
and SOS matching are not connected. The browser online indicator reflects
connectivity only.
