# AapdaSetu project instructions

Before making a change, read [`../CONTEXT.md`](../CONTEXT.md). It is the
canonical project overview and defines the prototype boundaries, architecture,
folder responsibilities, and coding conventions. Keep this file and
`CONTEXT.md` aligned when those decisions change.

## Project context

AapdaSetu follows the vision **"Swadeshi for Aatmanirbhar Bharat"** and covers
the disaster lifecycle: local risk and alerts before an event, safety guidance
and shelter routing during it, and SOS/volunteer coordination afterward.

The project vision is pan-India and multi-hazard, covering a broad range of
natural and human-made disasters. The current flood data/model work uses a
configurable regional dataset as one example; do not make test-region names,
station names, or sample data appear as the scope of the whole project or
hardcode them into general frontend experiences. Keep region-specific data in
configuration. Hazard modules must plug into the shared `HazardModule`
contract without coupling hazard-specific logic to routing, alerts, or SOS
matching.

The planned data inputs are archived IMD rainfall, CWC gauge/discharge,
ISRO MOSDAC/Bhuvan flood extent, and OSM road/shelter data. Do not invent
government data URLs or scrape restricted portals. Use a mock alert gateway;
real SMS and live deployment are out of scope. Region-aware Bhashini
localization and general PWA/offline caching are planned, not yet implemented.
IndexedDB is used for the implemented help/supply submission retry queue only.

The stack is Python 3.11/FastAPI/SQLAlchemy/GeoAlchemy2/PostGIS, with the
planned ML tools (pandas, scikit-learn, XGBoost, joblib, geopandas, rasterio,
xarray), APScheduler/httpx, osmnx/networkx routing, React/Vite, MapLibre GL or
Leaflet, i18next, and Docker Compose. See `CONTEXT.md` for the detailed folder
map and technology responsibilities.

## Project-specific guidance

- Keep current flood data/model work scoped to its configured study area, but
  design the platform and UI for all-India, multi-hazard use.
- Keep sample geography and station details out of general app-facing text.
- Keep routing, alerts, and SOS/matching logic independent of a specific
  hazard.
- Use archived Indian datasets as replay inputs. Never invent restricted data
  URLs or claim that a source is live.
- Do not dispatch real alerts. Use the mock alert gateway.
- Keep Bhashini credentials and service endpoints in environment configuration.
  Do not hard-code credentials or invent API endpoints or payload formats.
- Keep PWA guide/map caching modular; do not claim it is implemented until its
  service worker and local data storage are in place. The help/supply forms do
  have a separate IndexedDB submission queue with conflict triage.
- Prefer small, typed, documented changes that are straightforward to explain
  in a student project viva. Update `CONTEXT.md` when architecture or status
  changes.

## Current status

The repository includes backend/PostGIS scaffolding and a flood data-modelling
phase. Supplied local Bihar telemetry and daily discharge CSV schemas are
supported; Birpur Barrage is configured as a discharge candidate. Its official
station ID and danger discharge level remain TODOs. A chronological
2022-2023 train / 2024-2025 test split is configured with a 72-hour purge;
2025 has data only through May. Baisi_1 telemetry is not confirmed as Kosi.
Keep data work real-data-only:
use synthetic observations only in named unit-test fixtures. No real model
metrics or trained model exist yet. Prediction serving, replay, translation,
routing, matching, real alert dispatch, and offline caching are not implemented.
User authentication is implemented with verified email, Argon2 password hashes,
JWT access tokens invalidated by token-version changes on logout, and
responder/admin access checks. Local development email
uses Mailpit. Responder status is granted only after admin approval of a
verified user's role request; applicants remain ordinary users until approval.
Admin roles are initialized using operator-selected credentials through the
one-time bootstrap CLI; administrators can sign in with a username or email,
while regular accounts use email. The supply responder inbox is a persistent
human-coordination queue, not automated or emergency dispatch. Offers support
approved-responder assignment, actual pickup quantities, cancellation rollback,
and delivered tracking; EOC responders/admins can flag or close spam/duplicate
requests. Public submissions use shared rate limits, PostGIS distance sorting
when coordinates are explicitly supplied, and IndexedDB sync that parks
non-retryable 4xx conflicts for user review.
The frontend presents 14 hazard categories and hazard-specific safety guides
that expand directly within their cards as a Before/During/After table, with
emergency, ambulance, and relevant fire-service contact numbers. English
is the default; device location filters language choices through an approximate
local country-level lookup. Bhashini credentials are not configured, so the
local translation cache is used where available and uncached safety text
remains in English. Device coordinates are requested only after a user action
in the location-sharing flow and are not automatically transmitted or stored.
Forecasting, shelter operations, routing, translation service requests, real
dispatch, and PWA/offline map or guide caching remain unconnected. The separate
SOS demonstration form remains session-only; help and supply submissions are
connected to the persistent API.
