# AapdaSetu

A disaster-management platform designed to support communities across India
before, during, and after severe hazards including floods, cyclones, landslides,
droughts, heatwaves, and other natural or human-made emergencies.
Read [CONTEXT.md](./CONTEXT.md) for the full vision, boundaries, and status.

## Requirements

- Docker Desktop with Docker Compose
- Git

The backend and frontend dependencies are installed inside their containers.

## Run with Docker Compose

From the repository root in PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open the frontend at <http://localhost:5174> and the API health endpoint at
<http://localhost:8002/health>. Mailpit receives local verification messages at
<http://localhost:8025> using SMTP on `localhost:1025`. Stop the services with `Ctrl+C`; remove the
containers (while retaining the database volume) with:

```powershell
docker compose down
```

To also delete the local database volume and its data:

```powershell
docker compose down --volumes
```

The sample `.env` credentials are for local development only. Change them
before sharing the environment. The API does not create or alter database
tables on startup. Initialize a fresh database explicitly after starting the
services:

```powershell
docker compose exec backend alembic upgrade head
```

Before using authentication, set `AUTH_JWT_SECRET` in `.env` to a random secret
of at least 32 characters (for example, generate one with
`python -c "import secrets; print(secrets.token_urlsafe(48))"`). The sample file
leaves this value blank so the API refuses to issue or accept JWTs until it is
configured. Registration sends an email through the Compose Mailpit service;
open its inbox at <http://localhost:8025>, then follow the verification link.
Resending a link is available from the sign-in/register view. Local runs outside
Compose should set `SMTP_HOST=localhost`, `SMTP_PORT=1025`, and
`MAILPIT_UI_URL=http://localhost:8025`.

The responder checkbox submits a self-reported request; it does not verify
organizational affiliation or grant responder access. Applicants remain normal
community users until an administrator approves the request. To provision the
initial administrator after migration,
set `BOOTSTRAP_ADMIN_FULL_NAME`, a unique
`BOOTSTRAP_ADMIN_USERNAME` (3-32 letters, numbers, dots, underscores, or
hyphens), `BOOTSTRAP_ADMIN_EMAIL` (contact/verification address), and a unique
`BOOTSTRAP_ADMIN_PASSWORD` (at least 12 characters) in the ignored local `.env`,
then run the one-time command:

```powershell
docker compose exec backend python -m app.services.bootstrap_admin
```

This creates an email-verified admin account from the credentials you chose; no
default admin password is included in the repository. If an admin already
exists with the configured email but has no username, the command assigns that
username without changing the account password. Otherwise, it refuses to
create a second admin or reuse an existing username/email. Remove the bootstrap
values from `.env` after success. Sign in with the chosen username and password
to open **Admin accounts**; regular accounts can continue to sign in with their
email. Review pending responder applications and approve or reject each one.
Approving requires that user's email to be verified.
After rejection, the account remains a normal community account and can submit
a new responder-role request later.

Approved responder accounts can open the responder section; other verified
users retain normal community access. The inbox itself is still a browser-session
demonstration, not a shared SOS queue, and does not dispatch real requests.

For an existing local database previously initialized by the API, do not delete
the volume. The old startup code created tables without recording a migration.
Record that existing schema at the original baseline revision, then apply later
migrations. Stamping the baseline does not create, alter, or delete application
tables:

```powershell
docker compose exec backend alembic stamp 0001_initial_schema
docker compose exec backend alembic upgrade head
```

Then compare the live schema to the models:

```powershell
docker compose exec backend alembic check
```

If the comparison reports differences, do not run `upgrade head` on that
database yet; preserve its data and create a corrective migration for its actual
schema. `/health` reports API liveness independently of the database; `/ready`
reports database connectivity.

## Run the backend locally with Uvicorn

Activate an environment running Python 3.11, then change into `backend` before
starting Uvicorn because `app.main:app` is an application package in that folder:

```powershell
Set-Location C:\Users\Himanshu\Disaster-management
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
$env:DATABASE_HOST = "127.0.0.1"
$env:DATABASE_PORT = "5433"
$env:POSTGRES_USER = "aapdasetu"
$env:POSTGRES_PASSWORD = "change-me-for-local-development"
$env:POSTGRES_DB = "aapdasetu"
Set-Location backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

The default local database URL uses port `5433`, matching the host port
published by Compose. The backend builds its connection URL from these
components, including credentials with URL-reserved characters. `DATABASE_URL`
can still override this configuration when supplied as a properly encoded URL.
If you changed the Compose database credentials or port, set the corresponding
values before starting the local backend. Apply pending schema migrations after
rebuilding the Compose backend image:

```powershell
docker compose up --build -d backend
docker compose exec backend alembic upgrade head
```

Alternatively, stay in the repository root and set the application directory:

```powershell
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001 --reload
```

Verify `http://127.0.0.1:8001/health` and
`http://127.0.0.1:8001/api/v1/status`. The project currently uses Python 3.11;
do not rely on the existing `.venv` if it was created with Python 3.14.

## Read-only geography API

The backend exposes database-backed endpoints for the geographic catalog:

- `GET /api/regions?limit=100&offset=0` lists administrative regions.
- `GET /api/shelters?region_id=7&limit=100&offset=0` lists shelters, optionally
  filtered by region.

Both return JSON arrays; an empty table returns `[]`. Region boundaries and
shelter locations are GeoJSON geometries with coordinates in longitude,
latitude order. `limit` is between 1 and 500; `offset` is zero or greater.
Database query failures return HTTP 503. These endpoints return only records
stored in the database; they do not supply seeded or demonstration records.
Each response includes a verification status and source name/reference. Existing
records are labeled `unverified` with source `Unspecified (legacy record)`.
Optional source reference and license/attribution fields are included where
known.
New validated region/shelter import payloads require a source name and are
unverified by definition; the API does not expose import or verification writes.
Marking a record `verified` requires both a reviewer and review timestamp, and
still does not guarantee current safety or availability.

### Open telemetry ingestion foundation

`GET /api/telemetry/sentinels` performs an async, batched read from the
unauthenticated Open-Meteo Flood, Weather, and Elevation APIs plus the GDACS
India event feed. The provider adapters preserve hooks for future approved
IMD/CWC/MOSDAC/Bhuvan integration and do not claim that external data is an
authoritative warning or verified observation.

Coordinates are configured in `backend/app/config/sentinels.json`. Set
`TELEMETRY_SENTINELS_PATH` to use another JSON sentinel-grid file. The endpoint
requires network access and returns HTTP 503 if provider retrieval fails.
APScheduler polling and persistent ingestion are not yet implemented.

### Core V1 services

- `GET /api/v1/status` reports live telemetry, alert, shelter, routing, and translation initialization.
- `GET /api/v1/forecasts?refresh=true` polls the open-provider sentinel grid and returns prototype flood risk scores.
- `GET /api/v1/alerts?lang=hi&dispatch=true` translates an alert through Bhashini/deep-translator/local fallback and records mock delivery.
- `GET /api/v1/shelters/nearest?lat=...&lon=...&limit=5` finds verified PostGIS shelters or clearly labels Pan-India prototype entries.
- `GET /api/v1/local-readiness?lat=...&lon=...` returns coordinate-specific live-snapshot, verified-shelter, and routing readiness.
- `GET /api/v1/geocode?q=Supaul&limit=5` searches Indian place/district names and returns coordinates. Configure `GOOGLE_MAPS_API_KEY` for Google Geocoding; otherwise the backend uses OpenStreetMap/Nominatim as an open fallback.
- `POST /api/v1/route/evacuate?lat=...&lon=...` computes an OSMnx-preferred, NetworkX-cached evacuation route.

The shelter catalogue and hazard scores are prototypes. They are not verified
live operational emergency information.

### Offline dataset intake and registry

The shared registry tracks dataset family, evidence type, source/rights
references, coverage and period, freshness metadata, validation report, review
state, and publication state. The offline importer currently accepts only
region and shelter GeoJSON bundles. It validates a manifest and feature
structure, writes a JSON report, and is validation-only by default. `--stage`
stores records in dedicated quarantine tables; it never writes the operational
region or shelter tables. The read-only `GET /api/datasets` endpoint returns
paginated metadata only, and the geography catalog displays that metadata.

Example manifest (save as `manifest.json`):

```json
{
  "dataset_key": "sample-regions",
  "dataset_family": "administrative_geography",
  "evidence_type": "geography",
  "record_type": "regions",
  "source_name": "Example source",
  "source_reference": "Source documentation reference",
  "coverage": "Declared coverage",
  "rights_status": "unconfirmed"
}
```

From `backend\`, validate without staging:

```powershell
python -m app.services.import_dataset --manifest path\to\manifest.json --geojson path\to\regions.geojson --report path\to\report.json
```

Add `--stage` only when `DATABASE_URL` points to the intended PostGIS database
and its Alembic migrations are current. Staging is not approval: imports remain
`pending` and `quarantined`, and no review/publication workflow or operational
consumer exists. `rights_status: "documented"` records an operator-supplied
reference; it does not independently establish permission or legal clearance.
Do not import datasets until their source, terms, attribution, and permitted use
have been reviewed. The current GeoJSON importer does not support hazard
observations, warnings, exposure, roads, or other broader registry families.

To exercise the catalog end to end without changing the existing application
database, create a separate temporary database in the local PostGIS service:

```powershell
docker compose up -d db
docker compose exec -T db createdb -U aapdasetu aapdasetu_catalog_verify
$env:DATABASE_URL = "postgresql+psycopg://aapdasetu:change-me-for-local-development@127.0.0.1:5433/aapdasetu_catalog_verify"
python -m alembic -c backend\alembic.ini upgrade head
```

Insert explicitly synthetic records into that database only:

```powershell
docker compose exec -T db psql -U aapdasetu -d aapdasetu_catalog_verify -c "WITH new_region AS (INSERT INTO regions (name, region_type, district_name, boundary, source_name) VALUES ('SYNTHETIC E2E Region', 'district', 'SYNTHETIC', ST_GeomFromText('MULTIPOLYGON(((86 25,87 25,87 26,86 26,86 25)))', 4326), 'SYNTHETIC E2E fixture') RETURNING id) INSERT INTO shelters (name, region_id, capacity, current_occupancy, location, source_name) SELECT 'SYNTHETIC E2E Shelter', id, 25, 4, ST_GeomFromText('POINT(86.5 25.5)', 4326), 'SYNTHETIC E2E fixture' FROM new_region"
docker compose exec -T db psql -U aapdasetu -d aapdasetu_catalog_verify -c "INSERT INTO regions (name, region_type, district_name, boundary, source_name) VALUES ('SYNTHETIC Empty Region', 'block', 'SYNTHETIC', ST_GeomFromText('MULTIPOLYGON(((87 25,88 25,88 26,87 26,87 25)))', 4326), 'SYNTHETIC E2E fixture')"
```

In one PowerShell window, run the API from the backend directory with the same
`DATABASE_URL`:

```powershell
Set-Location backend
$env:DATABASE_URL = "postgresql+psycopg://aapdasetu:change-me-for-local-development@127.0.0.1:5433/aapdasetu_catalog_verify"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

In another window, run `npm --prefix frontend run dev`, then open the operations
center's **Database Catalog** tab at <http://127.0.0.1:5173>. Confirm the
synthetic region and shelter appear, filter by the region, and select the empty
region to check the empty-result state. Stop the API to confirm the page shows
an API error rather than static demonstration records.
Finally, drop only the temporary database and stop PostGIS:

```powershell
docker compose exec -T db dropdb -U aapdasetu aapdasetu_catalog_verify
docker compose stop db
```

This leaves the existing `aapdasetu` database and Docker volume intact.

## Run backend tests locally

Use Python 3.11 and install the development requirements:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest
python -m ruff check .
```

Health and catalog API unit tests do not require a running database. The API's database URL
defaults to a local PostGIS service at `localhost:5432` for local runs; Docker
Compose supplies its internal database URL automatically.

## Frontend

The React dashboard includes interactive preparedness, safety-guide,
request/volunteer, and data-readiness views. Fourteen disaster categories have
specific English safety guidance and the India emergency response number.
English is the default. Device location filters the language selector using a
local, approximate country-level lookup; a manual selector remains available.
If Bhashini credentials are not configured, cached interface translations are
used and uncached safety text stays in English. Hazard guides include common
emergency, ambulance, and relevant fire-service numbers; local availability
may vary, and 112 is the fallback. During a disaster, users can explicitly
request their device location and choose to share or copy it; coordinates are
not sent automatically. Select **View safety guide** on a hazard card to
expand its Before/During/After guidance and contacts directly in that card;
overview hazard cards open the corresponding expanded guide.

Forecasts, verified shelter locations, evacuation routes, alert delivery,
translation, and request matching are not currently available from the UI.
The operations-center **Database Catalog** tab fetches region and shelter
records from `/api/regions` and `/api/shelters`. It shows loading, empty, and
error states, supports filtering shelters by region, and labels returned
records with their verification and provenance metadata; current database
records default to unverified prototype data. The separate Shelter Demonstration
tab remains static and is not operational information. Vite proxies `/api` to
`http://127.0.0.1:8001` for local runs; Docker Compose proxies to the backend
service.
The connectivity indicator reflects browser connectivity only. Response form
entries appear in the in-app responder inbox for the current browser session,
but are held only in memory and disappear on reload; they are not sent to real
responders or emergency services. The page is not monitored for emergencies.

To run only the frontend locally:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL printed in the terminal (normally
<http://localhost:5173>). No additional frontend dependencies are required.

## Data audit and flood-model phase

The platform-wide data-family inventory and current source/access gaps are
documented in [`docs/data_inventory.md`](docs/data_inventory.md). The local-file
audit is a separate content summary and does not verify each file's source,
license, or operational fitness.

Audit locally supplied raw files without downloading or fabricating anything:

```powershell
python ml/data_audit.py
```

The Markdown report is written to `docs/data_audit_report.md`. With an empty
`ml/data/raw`, the report records that no real files were found.

The supplied manual discharge CSV is configured as the active candidate at
Birpur Barrage. The loader filters it using the site's name and Supaul/Birpur/
Kosi metadata. Telemetry and daily discharge source headers are normalized
without treating serial numbers as station IDs. No danger threshold or official
station ID has been inferred. Rainfall and an additional upstream series are
optional and currently unset.

The chronological split is set to train on 2022–2023 and test on 2024–2025;
the 2025 file ends in May, so the test period contains only one complete
monsoon season. A 72-hour purge excludes training examples whose label window
could overlap the test period. Treat any resulting metrics as preliminary.

Before training, obtain and enter Birpur's verified discharge danger threshold
and its official source in `ml/config.yaml`. Then run:

```powershell
python -m ml.training.train_xgboost
python -m ml.evaluation.evaluate_training_output
```

Run focused data/model unit tests with:

```powershell
python -m pytest backend/tests/test_flood_features.py
python -m ruff check ml backend/tests/test_flood_features.py
```

No synthetic values are used for model metrics. Synthetic fixtures are
labelled `SYNTHETIC` and exist only under `backend/tests/fixtures` for unit tests.

## Current boundaries

The health route and structural stubs are implemented. The flood data/modelling
scaffold includes loaders, feature/label construction, baselines, XGBoost
training, and metrics, but has no real data or trained result. No real
Bhashini request, evacuation route, alert dispatch, SOS matching, or PWA
caching is active yet. Never use the mock project configuration for real
emergency communications.
