# Falaaa project status

**Status:** First purchase-request backend milestone implemented; not production-ready
**Updated:** 2026-11-06
**Product:** React/Vite storefront with an independently maintained FastAPI API

## Architecture

The storefront remains a client-rendered React + TypeScript + Vite application. It retains the existing routes (`/`, `/orders`, `/agent`, and `/business`) and project-owned component/CSS system. The API is a separate Python 3.12+ service using FastAPI, Pydantic Settings, SQLAlchemy 2, and Alembic. PostgreSQL is the development/production database; tests use in-memory SQLite.

The API owns order persistence and status transitions. The frontend calls it through `src/lib/api.ts`; Vite proxies `/api/*` to a configurable local API target. No payment or supplier provider is selected or simulated.

## Implemented milestone

| Area | Current behavior |
|---|---|
| Database | PostgreSQL via `DATABASE_URL`; SQLAlchemy session management; Alembic migration creates catalogue/customer/order tables and clearly marked sample offers |
| Health | `GET /api/v1/health` checks the database and reports `503` without exposing connection details if it is unavailable |
| Catalogue | Lists MTN (`mtn`), Telecel (`telecel`), and AirtelTigo (`at`) and their available bundles; no live inventory is claimed |
| Customer | Stores a UUID, validated/normalized Ghanaian mobile number, and creation timestamp; retains no extra personal fields |
| Order | `POST /api/v1/orders` validates phone/network/bundle, persists a cryptographically referenced order, and starts at `pending_payment` |
| Lookup | `GET /api/v1/orders/{reference}` returns recorded status and a masked recipient number |
| History | `GET /api/v1/customers/me/orders` is scoped to the authenticated customer identity; returns `401` until real authentication is integrated |
| State machine | Service logic restricts transitions across pending payment, payment processing, paid, fulfillment pending, processing, completed, failed, cancelled, and refunded; no public mutation endpoint exists |
| Provider boundaries | Typed payment and fulfillment protocols define future integration points without initiating or recording provider activity |
| Frontend | Composer loads backend bundles and creates purchase requests; tracking looks up a reference and shows the returned order/status; API errors, loading, and sample-only cases are explicit |
| Local development | Docker Compose runs PostgreSQL and API; the API container applies migrations; Codespaces forwards frontend `5173` and API `8000` |

Seeded one-gigabyte, GHS 1.00 catalogue records are **development samples only**. They are marked `is_sample`; they are not production prices, supplier-confirmed availability, or fulfillment promises.

## Repository structure

```text
src/
  components/OrderComposer.tsx
  data/networks.ts
  lib/api.ts
  lib/phone.ts
  pages/
backend/
  app/api/routes/
  app/core/
  app/models/
  app/schemas/
  app/services/order_service.py
  alembic/versions/
  tests/
.devcontainer/devcontainer.json
docker-compose.yml
```

## Implemented API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/health` | API/database health |
| `GET` | `/api/v1/networks` | Supported network catalogue |
| `GET` | `/api/v1/networks/{network_id}/bundles` | Available bundles for a network |
| `GET` | `/api/v1/bundles/{bundle_id}` | Retrieve a bundle |
| `POST` | `/api/v1/orders` | Persist an order request as `pending_payment` |
| `GET` | `/api/v1/orders/{reference}` | Look up an order by unguessable reference |
| `GET` | `/api/v1/customers/me/orders` | Customer history behind authentication (currently unavailable) |

FastAPI docs are served at `/api/docs`. Configuration comes from `DATABASE_URL` and `CORS_ORIGINS`; the frontend uses `VITE_API_BASE_URL` and `API_PROXY_TARGET`.

## Verification commands

```bash
# Repository root
npm test
npm run build

# Backend directory
python -m pip install -r requirements.txt
python -m pytest -q
alembic upgrade head
```

The test suite covers health/database checks, phone validation, catalogue behavior, order creation and lookup, reference uniqueness, history privacy, and disallowed public status changes.

## Deferred work and launch gates

- Integrate a real customer/agent identity provider and verified OTP delivery. Until then, keep history and administrative actions inaccessible; do not use caller-supplied phone numbers as authorization.
- Select a licensed payment provider and an approved supplier for each network only after reviewing their contracts, API documentation, sandbox behavior, callback authentication, idempotency, reconciliation, delivery, cancellation, refund, and dispute semantics.
- Implement real payment and fulfillment adapters behind the typed provider interfaces. Record payment attempts only when real payment initiation exists; transition to `paid` only on a verified provider event; mark completion only after verified supplier delivery.
- Establish production catalogue/pricing sources, operational monitoring/alerts, request throttling, retention/privacy policy, support workflows, and deployment/hosting region before launch.
- Keep provider credentials in managed secrets or environment configuration. Never request/store mobile-money PINs, passwords, or OTP values.

Azure Container Apps, Azure Functions, queue/blob storage, named provider candidates, and launch volumes remain proposals—not deployed services or verified integrations.
