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
- Planned offline support is a PWA with cached risk maps, shelter coordinates,
  and precomputed evacuation routes. It is not implemented yet.

## Technology stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy, GeoAlchemy2, PostgreSQL/PostGIS,
  Alembic, APScheduler, and httpx for the Bhashini wrapper.
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

**Backend scaffolding and flood data-modelling phase started.** The repository
contains a FastAPI `/health` endpoint,
environment-based configuration, a SQLAlchemy engine configured for PostGIS,
initial spatial domain models, a `HazardModule` contract and `FloodModule`
stub, a Bhashini client stub, basic Docker Compose services, a React/Vite shell,
and a passing health-endpoint test.

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
observations are used only in labelled unit-test fixtures. Database migrations,
hazard prediction serving, archived-data replay, translation requests/cache,
map/routing, mock alert workflow, SOS matching, and PWA offline storage are not
implemented.

The frontend presents AapdaSetu as an all-India, multi-hazard platform with
interactive cards for 14 natural and human-made hazard categories and
hazard-specific English safety guidance for before, during, and after an event.
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
includes local-only SOS/volunteer form previews and data-readiness details.
Forecasts, verified shelters, routing, alert dispatch, and matching are not
connected. The browser online indicator reflects connectivity only. The
application is not an emergency service.
