# Falaaa

Falaaa is a responsive Ghanaian mobile-data marketplace prototype for MTN, Telecel, and AirtelTigo (AT). The repository contains a React storefront and an independently runnable FastAPI purchase-request API.

## Architecture

- **Frontend:** React 19, TypeScript, Vite, and React Router.
- **Backend:** Python 3.12+, FastAPI, Pydantic Settings, SQLAlchemy 2, and Alembic.
- **Database:** PostgreSQL for local/deployed use; SQLite in automated API tests.
- **Tests:** Vitest for frontend utilities and pytest for the backend.
- **API boundaries:** The API owns catalogue reads, customer records, order creation, order lookup, and controlled internal order-state transitions. The frontend only submits requests and displays API responses.

```text
src/
  components/       # storefront components, including the order composer
  data/             # presentation details for supported Ghanaian networks
  lib/api.ts        # shared API client and API response types
  pages/            # React Router pages
backend/
  app/api/routes/   # health, networks, bundles, orders, customer history
  app/core/         # settings, database session, authentication foundation
  app/models/       # SQLAlchemy catalogue, customer, and order models
  app/schemas/      # Pydantic request/response validation
  app/services/     # order creation and state transition rules
  alembic/          # versioned database schema and sample catalogue seed
  tests/            # API, phone-validation, and state-transition tests
```

## Local setup

### Docker Compose (PostgreSQL and API)

Docker Compose starts PostgreSQL and the API; the API container applies Alembic migrations before serving requests.

```bash
cp .env.example .env
# Change POSTGRES_PASSWORD in .env to a private local value.
docker compose up --build -d
```

The API listens on port `8000`; PostgreSQL is available on port `5432`. The Codespaces configuration forwards ports `5173` and `8000`. The Compose password fallback is for local development only and must never be reused in a deployed environment.

### Frontend

```bash
npm install
npm run dev
```

The Vite development server proxies `/api/*` to `API_PROXY_TARGET` (default `http://localhost:8000`). Set `VITE_API_BASE_URL` to `/api/v1` for the local proxy or to the deployed API base URL, including `/api/v1`, for a separately hosted frontend. Configure that API's `CORS_ORIGINS` for the actual frontend origin; do not hardcode a Codespaces forwarding URL.

### Run the API without the API container

Start just the local PostgreSQL service, then create a backend virtual environment and run the API from `backend/`:

```bash
docker compose up -d db
cd backend
cp .env.example .env
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`DATABASE_URL` and `CORS_ORIGINS` are read from the environment or `backend/.env`. Never commit `.env` files or real credentials. `.env.example` files contain local-development settings/placeholders only.

## API

The interactive API documentation is available at `http://localhost:8000/api/docs`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/health` | API and database connectivity (`200` when reachable, `503` otherwise) |
| `GET` | `/api/v1/networks` | Supported networks: `mtn`, `telecel`, `at` |
| `GET` | `/api/v1/networks/{network_id}/bundles` | Available bundle records for one network |
| `GET` | `/api/v1/bundles/{bundle_id}` | Retrieve a bundle |
| `POST` | `/api/v1/orders` | Create a purchase request |
| `GET` | `/api/v1/orders/{reference}` | Retrieve order status using its unguessable reference |
| `GET` | `/api/v1/customers/me/orders` | Authenticated customer history; returns `401` until real authentication is integrated |

Create a request with:

```json
{
  "phone": "+233 24 123 4567",
  "network_id": "mtn",
  "bundle_id": "mtn-sample-1gb"
}
```

The API validates Ghanaian mobile numbers with `phonenumbers`, normalizes them to E.164, validates catalogue IDs, creates/reuses a minimal customer record, and persists the new order as `pending_payment`. Order references are generated with cryptographic randomness. Lookup results expose only a masked phone number. There is deliberately no public order-status mutation endpoint; state transitions are validated by the backend service.

The initial Alembic migration seeds one clearly marked **sample-only** bundle per supported network at an illustrative amount. These are development fixtures, not verified offers, production prices, supplier inventory, or a promise to fulfill orders. The frontend labels sample offers/orders and does not claim that payment or delivery occurred.

## Checks

```bash
# Frontend
npm test
npm run build

# Backend (from repository root)
cd backend
python -m pip install -r requirements.txt
python -m pytest -q
alembic upgrade head
```

Backend tests use an in-memory SQLite database. To verify PostgreSQL connectivity and migrations locally, start the Compose services and check `GET /api/v1/health`; the API container applies migrations on startup.

## Known limitations and integration requirements

- Phone-based OTP, customer sessions, agent accounts, and administrative authentication are **not implemented**. Customer history stays protected and unavailable until a real authentication provider and identity-to-customer mapping exist.
- The order starts at `pending_payment`. No payment attempt, payment confirmation, fulfillment request, or completion is fabricated; public callers cannot set status.
- Payment and mobile-data supplier providers are not selected or integrated. Before integration, obtain provider API documentation and sandbox access, commercial/licensing agreements, callback-signing and idempotency specifications, reconciliation/refund rules, and production credentials. Store real credentials in a managed secret store/environment, never in source control.
- Production pricing, catalogue validity, payment callbacks, supplier delivery confirmation, cancellation/refund automation, rate limiting, and operational monitoring need to be designed and verified before launch.
- Bundle checkout currently creates a persisted purchase request only. It does not charge a customer or deliver mobile data.
