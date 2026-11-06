# Falaaa project status

**Status:** Customer account and purchase-request milestones implemented; not production-ready
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
| Customer accounts | UUID customer records store full name, normalized unique Ghanaian phone, Argon2id password hash, verification/account status, role, and timestamps |
| Authentication | Registration, login, logout, session profile, and CSRF-token endpoints; opaque random session tokens are hashed in the database and issued only as HttpOnly cookies |
| Account protections | Login/registration throttles use database-backed windows; private APIs enforce the session, CSRF, and allowed-origin checks; login errors are generic |
| Provider-dependent account features | Phone verification, resend, and password recovery/reset endpoints explicitly return unavailable until a real SMS/recovery provider and verified workflow are configured |
| Order | `POST /api/v1/orders` validates phone/network/bundle, persists a cryptographically referenced order, and starts at `pending_payment` |
| Lookup | `GET /api/v1/orders/{reference}` returns recorded status and a masked recipient number |
| History | `GET /api/v1/customers/me/orders` is scoped to the authenticated account owner; anonymous/legacy orders are not exposed by matching phone number |
| State machine | Service logic restricts transitions across pending payment, payment processing, paid, fulfillment pending, processing, completed, failed, cancelled, and refunded; no public mutation endpoint exists |
| Provider boundaries | Typed payment and fulfillment protocols define future integration points without initiating or recording provider activity |
| Frontend | `/signup`, `/login`, `/dashboard`, and `/forgot-password` are wired to the API; route guards, session restoration, and actual logout are implemented |
| Customer journey | The composer submits requests using the authenticated session; the dashboard shows real profile/history, and order lookup displays API status; loading, errors, empty states, and sample-only cases are explicit |
| Local development | Docker Compose runs PostgreSQL and API; the API container applies migrations; Codespaces forwards frontend `5173` and API `8000` |

Seeded one-gigabyte, GHS 1.00 catalogue records are **development samples only**. They are marked `is_sample`; they are not production prices, supplier-confirmed availability, or fulfillment promises.

## Repository structure

```text
src/
  components/OrderComposer.tsx
  auth/
  data/networks.ts
  lib/api.ts
  lib/phone.ts
  pages/                  # storefront, signup/login, dashboard, tracking
backend/
  app/api/routes/
  app/core/               # settings, database, session/CSRF/rate-limit security
  app/models/             # customers, orders, catalogue, sessions, rate limits
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
| `POST` | `/api/v1/auth/register` | Register a phone-unverified customer and create a session |
| `POST` | `/api/v1/auth/login` | Verify credentials and create a session |
| `POST` | `/api/v1/auth/logout` | Revoke the current session (CSRF protected) |
| `GET` | `/api/v1/auth/me` | Return the authenticated customer |
| `GET` | `/api/v1/auth/csrf` | Issue/refresh a CSRF token for browser requests |
| `POST` | `/api/v1/auth/forgot-password` | Rate-limited; unavailable until a recovery provider is configured |
| `POST` | `/api/v1/auth/reset-password` | Unavailable until a verified reset-token workflow exists |
| `POST` | `/api/v1/auth/verify-phone` | Unavailable until a real SMS verification provider is configured |
| `POST` | `/api/v1/auth/resend-verification` | Unavailable until a real SMS provider is configured |
| `POST` | `/api/v1/orders` | Persist an order request as `pending_payment` |
| `GET` | `/api/v1/orders/{reference}` | Look up an order by unguessable reference |
| `GET` | `/api/v1/customers/me` | Return the authenticated customer profile |
| `GET` | `/api/v1/customers/me/orders` | Return only orders linked to the authenticated account |

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

The test suite covers health/database checks, phone validation, catalogue behavior, order creation and lookup, reference uniqueness, account registration and login, password hashing, session and CSRF behavior, rate limiting, logout, history privacy, and disallowed public status changes.

## Deferred work and launch gates

- Connect an approved SMS provider before enabling phone verification/resend. Accounts remain explicitly phone-unverified; no OTP is generated or reported as sent.
- Connect a verified messaging provider and implement expiring, single-use reset tokens before enabling password recovery. Recovery/reset endpoints report unavailable in the meantime.
- Define and enforce administrative authorization before adding any order-status mutation endpoint. No public admin/status-management endpoint is currently exposed.
- Select a licensed payment provider and an approved supplier for each network only after reviewing their contracts, API documentation, sandbox behavior, callback authentication, idempotency, reconciliation, delivery, cancellation, refund, and dispute semantics.
- Implement real payment and fulfillment adapters behind the typed provider interfaces. Record payment attempts only when real payment initiation exists; transition to `paid` only on a verified provider event; mark completion only after verified supplier delivery.
- Establish production catalogue/pricing sources, operational monitoring/alerts, trusted-proxy configuration, retention/privacy policy, support workflows, and deployment/hosting region before launch.
- Keep provider credentials in managed secrets or environment configuration. Never request/store mobile-money PINs, passwords, or OTP values.

Azure Container Apps, Azure Functions, queue/blob storage, named provider candidates, and launch volumes remain proposals—not deployed services or verified integrations.
