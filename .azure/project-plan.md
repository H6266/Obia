# Falaaa project status

**Status:** Customer journey and Stage 1 owner/admin operations implemented; not production-ready
**Updated:** 2026-11-06
**Product:** React/Vite storefront with an independently maintained FastAPI API

## Architecture

The storefront remains a client-rendered React + TypeScript + Vite application. It retains the existing routes (`/`, `/orders`, `/agent`, and `/business`) and project-owned component/CSS system. The API is a separate Python 3.12+ service using FastAPI, Pydantic Settings, SQLAlchemy 2, and Alembic. PostgreSQL is the development/production database; tests use in-memory SQLite.

The API owns order persistence and status transitions. The frontend calls it through `src/lib/api.ts`; Vite proxies `/api/*` to a configurable local API target. No payment or supplier provider is selected or simulated.

## Implemented milestone

| Area | Current behavior |
|---|---|
| Database | PostgreSQL via `DATABASE_URL`; SQLAlchemy session management; Alembic through `0009_order_integrity` creates catalogue, identity, authorization, order, and audit structures while preserving existing records and clearly marked sample offers |
| Health | `GET /api/v1/health` checks the database and reports `503` without exposing connection details if it is unavailable |
| Catalogue | Lists MTN (`mtn`), Telecel (`telecel`), and AirtelTigo (`at`) and their available bundles; no live inventory is claimed |
| Customer accounts | A shared UUID `User` principal stores credentials and account status; a customer profile stores customer data and links to that principal. Guest profiles remain unlinked, and existing customer/staff credentials were backfilled to distinct users without automatic merging |
| Authentication | Registration, login, logout, session profile, and CSRF-token endpoints; opaque random session tokens are hashed in the database and issued only as HttpOnly cookies |
| Account protections | Login/registration throttles use database-backed windows; private APIs enforce the session, CSRF, and allowed-origin checks; login errors are generic |
| Provider-dependent account features | Phone verification, resend, and password recovery/reset endpoints explicitly return unavailable until a real SMS/recovery provider and verified workflow are configured |
| Order | `POST /api/v1/orders` validates phone/network/bundle, requires an idempotency key, persists a cryptographically referenced order, and starts at `pending_payment`; conflicting reuse is rejected |
| Order integrity | Unique idempotency digest, positive amount, and a composite foreign key prevent mismatched bundle/network pairs; catalogue price snapshots remain unchanged when catalogue prices are edited |
| Lookup | `GET /api/v1/orders/{reference}` returns recorded status and a masked recipient number |
| History | `GET /api/v1/customers/me/orders` is scoped to the authenticated account owner; anonymous/legacy orders are not exposed by matching phone number |
| State machine | Service logic restricts transitions across pending payment, payment processing, paid, fulfillment pending, processing, completed, failed, cancelled, and refunded; no public mutation endpoint exists |
| Provider boundaries | Typed payment and fulfillment protocols define future integration points without initiating or recording provider activity |
| Frontend | `/signup`, `/login`, `/dashboard`, and `/forgot-password` are wired to the API; route guards, session restoration, and actual logout are implemented |
| Customer journey | The composer submits requests using the authenticated session; the dashboard shows real profile/history, and order lookup displays API status; loading, errors, empty states, and sample-only cases are explicit |
| Staff identity | A staff profile and session link to the shared `User` principal; customers cannot become staff through public signup; one Owner is initialized only through the interactive backend CLI. There is no verified customer/staff account-linking flow yet |
| Staff security | Argon2id passwords, mandatory TOTP MFA, encrypted TOTP secrets, one-time invitations, database-backed relational role/permission checks on every admin API, separate CSRF-protected HttpOnly cookies, and stricter database-backed login limits |
| Catalogue management | Staff can search and paginate the catalogue, update bundle attributes and network activation with a reason, and read append-only revision history; every mutation is permission-checked and audited |
| Owner/admin console | Separate `admin/` React/Vite app on port `5174`; real database-backed overview, date presets/custom range, orders centre, customer lookup/details/status controls, staff invitations, catalogue management, support notes/escalations, and audit history |
| Operations safeguards | Financial metrics without verified records are explicitly unavailable; sample orders excluded from business metrics; sensitive customer phones masked by default; customer suspension requires a reason and revokes sessions |
| Audit/history | Administrative audit records and order events are append-only in PostgreSQL; customer/order access and changes have actor, request ID, resource, time, and relevant reason/value records |
| Local development | Docker Compose runs PostgreSQL and API; the API container applies migrations; Codespaces forwards customer `5173`, admin `5174`, and API `8000` |

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
admin/
  src/auth/               # independent staff session state
  src/pages/              # operations overview, orders, customers, staff, audit
  src/services/api.ts     # admin API client; no business logic
backend/
  app/api/routes/         # customer and permission-protected staff APIs
  app/core/               # settings, database, customer session security
  app/models/             # customers, orders, staff, invitations, audit, events
  app/schemas/
  app/services/           # order state rules, admin RBAC/session/audit
  alembic/versions/
  scripts/bootstrap_owner.py
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
| `GET` | `/api/v1/admin/catalogue/networks` | Staff catalogue network list |
| `PATCH` | `/api/v1/admin/catalogue/networks/{network_id}/status` | Permission-checked activation change with audit record |
| `GET` | `/api/v1/admin/catalogue/bundles` | Paginated staff catalogue list |
| `PATCH` | `/api/v1/admin/catalogue/bundles/{bundle_id}` | Permission-checked update with reason and immutable revision history |
| `GET` | `/api/v1/admin/catalogue/bundles/{bundle_id}/history` | Catalogue revision history |
| `POST` | `/api/v1/admin/auth/login` | Staff password + TOTP login; separate staff session cookie |
| `POST` | `/api/v1/admin/auth/accept-invitation` | Accept one-time staff invite and begin MFA enrollment |
| `POST` | `/api/v1/admin/auth/confirm-enrollment` | Verify MFA and activate invited staff |
| `GET` | `/api/v1/admin/auth/me` | Current staff account and permissions |
| `POST` | `/api/v1/admin/auth/logout` | Revoke staff session (CSRF protected) |
| `GET/POST` | `/api/v1/admin/staff/invitations` | Owner-authorized invitation management; raw token returned only once |
| `GET` | `/api/v1/admin/staff` and `/roles` | Staff list and role permissions |
| `GET` | `/api/v1/admin/dashboard` | Date-filtered database metrics; unavailable financial/inventory values remain null |
| `GET` | `/api/v1/admin/orders` and `/orders/{reference}` | Search/filter/paginate and inspect orders; no manual paid/delivered action |
| `POST` | `/api/v1/admin/orders/{reference}/notes` and `/escalations` | Permission-controlled internal operational records |
| `GET` | `/api/v1/admin/customers` and `/customers/{id}` | Masked search, profile, order history, and support notes |
| `POST` | `/api/v1/admin/customers/{id}/status` | Reasoned suspension/reactivation; suspending revokes customer sessions |
| `GET` | `/api/v1/admin/audit` | Read append-only administrative audit history |

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
- Implement a verified account-linking flow before linking customer and staff profiles. Existing profiles remain linked to distinct `User` records until both accounts can be proven; phone verification requires an SMS provider.
- Any future order-state action must be backed by verified payment/supplier evidence and must not be a manual status override.
- Select a licensed payment provider and an approved supplier for each network only after reviewing their contracts, API documentation, sandbox behavior, callback authentication, idempotency, reconciliation, delivery, cancellation, refund, and dispute semantics.
- Implement real payment and fulfillment adapters behind the typed provider interfaces. Record payment attempts only when real payment initiation exists; transition to `paid` only on a verified provider event; mark completion only after verified supplier delivery.
- Establish production catalogue/pricing sources, operational monitoring/alerts, trusted-proxy configuration, retention/privacy policy, support workflows, and deployment/hosting region before launch.
- Stage 2 inventory/suppliers, Stage 3 double-entry financials/refunds/agent commissions, and Stage 4 businesses/alerts/forecasting/reports/exports/approval workflows remain unimplemented; do not expose placeholder metrics or actions.
- Configure and securely back up `STAFF_MFA_ENCRYPTION_KEY`; it is required for staff onboarding and recovery of encrypted TOTP seeds. Use HTTPS and secure cookies outside local development.
- Keep provider credentials in managed secrets or environment configuration. Never request/store mobile-money PINs, passwords, or OTP values.

Azure Container Apps, Azure Functions, queue/blob storage, named provider candidates, and launch volumes remain proposals—not deployed services or verified integrations.
