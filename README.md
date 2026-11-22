# AapdaSetu

AapdaSetu is a pan-India, all-hazard disaster-management platform for preparedness, safety guidance, incident coordination, and disaster-data workflows across the disaster lifecycle: prepare, respond, and recover.

The project follows the vision **“Swadeshi for Aatmanirbhar Bharat”** and brings multilingual guidance, geographic information, community coordination, and data-driven planning into a shared platform.

> [!IMPORTANT]
> AapdaSetu is not an emergency service or an official warning system. Do not use it for real emergency decisions or dispatch. External provider data, sample records, mock alerts, and non-authoritative forecasts require verification by the relevant authorities before operational use.

For the canonical architecture and implementation boundaries, see [CONTEXT.md](./CONTEXT.md). A detailed product and capability overview is available in [APPLICATION_CAPABILITIES_AND_FUTURE_SCOPE.md](./APPLICATION_CAPABILITIES_AND_FUTURE_SCOPE.md).

## Implemented capabilities

- All-hazard interface covering 14 natural and human-made disaster categories.
- Database-backed Before, During, and After safety guidance.
- English and Hindi interface support with a local fallback cache.
- Email verification, Argon2 password hashing, JWT authentication, and role checks.
- Community, responder, administrator, and super-administrator workflows.
- Persistent help requests and supply offers with assignment and delivery tracking.
- Incident, shelter-status, SOS, safety-tip, and account administration.
- PostgreSQL/PostGIS geographic catalog with Alembic migrations.
- Open-provider telemetry, geocoding, shelter lookup, and routing foundations.
- Region and shelter GeoJSON validation and quarantined dataset staging.
- Browser IndexedDB retry for recoverable coordination submissions.
- Flood audit, feature engineering, baseline, XGBoost, and evaluation workflows.

## Technology stack

| Area | Technologies |
| --- | --- |
| Frontend | React 18, Vite 7, Vitest |
| Backend | Python 3.11, FastAPI, Pydantic, SQLAlchemy, APScheduler |
| Database | PostgreSQL 16, PostGIS 3.4, Alembic |
| Geospatial | GeoAlchemy2, psycopg, NetworkX, OSMnx |
| Authentication | Argon2 via pwdlib, PyJWT, aiosmtplib |
| Machine learning | pandas, scikit-learn, XGBoost, joblib |
| Infrastructure | Docker Compose, Mailpit |

## Repository structure

```text
backend/app/api/          FastAPI route modules
backend/app/core/         Configuration and database setup
backend/app/hazards/      Shared hazard contract and implementations
backend/app/models/       SQLAlchemy and PostGIS models
backend/app/services/     Import, live-data, and domain services
backend/tests/            Backend pytest suite
frontend/src/             React application source
frontend/src/pages/       Main application views
frontend/src/components/  Reusable UI components
frontend/src/data/        Hazard and application data
ml/data/                  Raw and processed data locations
ml/training/              Loaders, features, and training workflows
ml/evaluation/            Metrics and evaluation utilities
docs/                     Data inventory and audit documentation
```

## Requirements

- Docker Desktop with Docker Compose
- Git
- PowerShell
- Python 3.11 for backend and data workflows
- Node.js and npm for frontend development

## Quick start with Docker Compose

### 1. Create the local environment file

From the repository root:

```powershell
Copy-Item .env.example .env
```

Generate a JWT secret of at least 32 characters:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set `AUTH_JWT_SECRET` in `.env` to the generated value. The database, email, and account values in `.env.example` are for disposable local development.

### 2. Start the services

```powershell
docker compose up --build
```

| Service | Address |
| --- | --- |
| Frontend | http://localhost:5174 |
| API health | http://localhost:8002/health |
| API documentation | http://localhost:8002/docs |
| Database readiness | http://localhost:8002/ready |
| Mailpit inbox | http://localhost:8025 |

PostgreSQL is published on `127.0.0.1:5433` and SMTP on `127.0.0.1:1025`.

### 3. Apply database migrations

The API does not create or modify tables when it starts. Apply migrations in a second terminal:

```powershell
docker compose exec backend alembic upgrade head
```

Check the migrated database against the SQLAlchemy models:

```powershell
docker compose exec backend alembic check
```

Stop the stack with `Ctrl+C`. Keep the database volume while removing containers:

```powershell
docker compose down
```

Remove the database volume as well:

```powershell
docker compose down --volumes
```

## Authentication and administration

Registration requires email verification. Local verification messages are handled by Mailpit at http://localhost:8025.

Create the initial administrator with these one-time operator-selected values in `.env`:

- `BOOTSTRAP_ADMIN_FULL_NAME`
- `BOOTSTRAP_ADMIN_USERNAME`
- `BOOTSTRAP_ADMIN_EMAIL`
- `BOOTSTRAP_ADMIN_PASSWORD`

Then run:

```powershell
docker compose exec backend python -m app.services.bootstrap_admin
```

Remove the bootstrap credentials from `.env` after successful setup. Administrators can sign in with their username or email; regular users sign in with email.

The responder checkbox creates a pending role request. A verified administrator must approve or reject the request. Role approval does not independently verify organizational affiliation.

## Migrating an existing database

Do not delete an older database that was initialized by application startup code. Record the existing schema at the baseline migration, then apply later migrations:

```powershell
docker compose exec backend alembic stamp 0001_initial_schema
docker compose exec backend alembic upgrade head
docker compose exec backend alembic check
```

Stamping does not create, alter, or delete tables. If `alembic check` reports schema differences, preserve the database and add a corrective migration for its actual state.

## Local backend and frontend development

### Backend

Create a Python 3.11 environment and start PostgreSQL and Mailpit:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
docker compose up -d db mailpit

$env:DATABASE_HOST = "127.0.0.1"
$env:DATABASE_PORT = "5433"
$env:POSTGRES_USER = "aapdasetu"
$env:POSTGRES_PASSWORD = "change-me-for-local-development"
$env:POSTGRES_DB = "aapdasetu"
$env:SMTP_HOST = "127.0.0.1"
$env:SMTP_PORT = "1025"
$env:MAILPIT_UI_URL = "http://127.0.0.1:8025"

python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001 --reload
```

Verify:

- http://127.0.0.1:8001/health
- http://127.0.0.1:8001/api/v1/status

`DATABASE_URL` can override the component-based database configuration when it contains a complete, URL-encoded PostgreSQL connection string.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Vite normally serves the interface at http://127.0.0.1:5173. Local `/api` requests are proxied to `http://127.0.0.1:8001`; Docker Compose proxies API traffic to the backend container.

## API overview

| Area | Example endpoints |
| --- | --- |
| Health | `/health`, `/ready` |
| Authentication | `/api/auth/register`, `/api/auth/login`, `/api/auth/logout` |
| Geography | `/api/regions`, `/api/shelters`, `/api/datasets` |
| Telemetry | `/api/telemetry/sentinels` |
| V1 services | `/api/v1/status`, `/api/v1/forecasts`, `/api/v1/local-readiness` |
| Incidents | `/api/incidents` and incident-linked SOS endpoints |
| Coordination | `/api/coordination/requests`, `/api/coordination/offers` |
| Safety | `/api/safety/tips` |
| Administration | `/api/admin/*`, `/api/super-admin/*` |

Interactive API documentation is available at `/docs`.

## Dataset registry and offline import

The registry stores dataset family, evidence type, source and rights references, coverage, freshness, validation, review, and publication metadata.

Validate region or shelter GeoJSON data from `backend\`:

```powershell
python -m app.services.import_dataset --manifest path\to\manifest.json --geojson path\to\regions.geojson --report path\to\report.json
```

Stage records only in a reviewed PostGIS database with current migrations:

```powershell
python -m app.services.import_dataset --manifest path\to\manifest.json --geojson path\to\shelters.geojson --stage --report path\to\report.json
```

Staging is not approval or verification. Rights metadata supplied by an operator does not independently establish permission or legal clearance. Review source, license, attribution, and permitted use before importing or operationalizing a dataset.

## Tests

Backend tests and lint:

```powershell
python -m pytest
python -m ruff check .
```

Focused flood-feature tests:

```powershell
python -m pytest backend/tests/test_flood_features.py
python -m ruff check ml backend/tests/test_flood_features.py
```

Frontend tests and build:

```powershell
npm --prefix frontend test
npm --prefix frontend run build
```

Most unit tests do not require a running database. Integration flows that read geographic or coordination data require PostgreSQL/PostGIS.

## Flood data workflow

The data-family inventory is documented in [docs/data_inventory.md](./docs/data_inventory.md). The local-file audit is documented in [docs/data_audit_report.md](./docs/data_audit_report.md).

Audit supplied local files without downloading or fabricating data:

```powershell
python ml/data_audit.py
```

The chronological split uses 2022–2023 for training and 2024–2025 for testing, with a 72-hour purge. Supplied files include a daily discharge series associated with Birpur Barrage and Bihar telemetry. The official station ID and verified danger-discharge threshold remain unknown and must not be inferred.

Synthetic observations are used only in explicitly labeled unit-test fixtures. Before real training, verify the source metadata and enter the official threshold in `ml/config.yaml`, then run:

```powershell
python -m ml.training.train_xgboost
python -m ml.evaluation.evaluate_training_output
```

No real model metrics or trained operational model are currently present in the repository.

## Operational boundaries

- External telemetry and provider flood scores are not authoritative observations.
- No official alert or SMS dispatch is active.
- No verified real-data flood forecast is currently served.
- Shelter, incident, and occupancy information requires operator verification and must not be assumed to reflect live conditions.
- Automated SOS matching, live road closure, rescue dispatch, and historical replay are not connected.
- Bhashini credentials are not configured; uncached text remains in English.
- PWA map and route caching are not implemented.
- Browser connectivity indicates network state only, not hazard status.
- Coordination submissions are human-managed workflows, not emergency dispatch.

## Documentation

- [Project context](./CONTEXT.md)
- [Application capabilities and future scope](./APPLICATION_CAPABILITIES_AND_FUTURE_SCOPE.md)
- [Platform data inventory](./docs/data_inventory.md)
- [Local data audit report](./docs/data_audit_report.md)
- [Docker Compose configuration](./docker-compose.yml)
