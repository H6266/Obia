# Obia

Obia is a responsive Ghanaian mobile-data marketplace prototype for MTN, Telecel, and AirtelTigo (AT). The repository contains a customer React app, a separate staff operations React app, and one independently runnable FastAPI/PostgreSQL backend.

## Architecture

- **Frontend:** React 19, TypeScript, Vite, and React Router.
- **Operations frontend:** Separate React 19, TypeScript, Vite app under `admin/`; it has no independent database or business rules.
- **Backend:** Python 3.12+, FastAPI, Pydantic Settings, SQLAlchemy 2, and Alembic.
- **Account security:** A shared `User` principal holds credentials and account state; customer and staff profiles remain distinct and existing accounts are not automatically merged. Passwords use Argon2id, staff requires TOTP MFA, and opaque database-backed HttpOnly sessions use CSRF validation and database-backed rate limits.
- **Database:** PostgreSQL for local/deployed use; SQLite in automated API tests. Alembic migrations through `0009_order_integrity` provide shared identities, relational staff roles/permissions, catalogue revision history, order idempotency, and order-to-catalogue integrity.
- **Tests:** Vitest for frontend utilities and pytest for the backend.
- **API boundaries:** The API owns catalogue reads, customer records, order creation, order lookup, and controlled internal order-state transitions. The frontend only submits requests and displays API responses.

```text
src/
  components/       # storefront components, including the order composer
  data/             # presentation details for supported Ghanaian networks
  lib/api.ts        # shared API client and API response types
  pages/            # React Router pages
backend/
  app/api/routes/   # customer, catalogue, order, and role-protected admin APIs
  app/core/         # settings, database session, cookie/session security
  app/models/       # SQLAlchemy catalogue, customer, order, staff, and audit models
  app/schemas/      # Pydantic request/response validation
  app/services/     # order state rules, staff permissions, audit and session security
  alembic/          # versioned database schema and sample catalogue seed
  tests/            # customer, admin/RBAC, phone, and order service tests
src/auth/           # shared authenticated customer state
src/pages/          # storefront and customer account pages
admin/src/          # separate staff login, dashboard, orders, customers, audit, staff
```

## Local setup

### Docker Compose (PostgreSQL and API)

Docker Compose starts PostgreSQL and the API; the API container applies Alembic migrations before serving requests.

```bash
cp .env.example .env
# Change POSTGRES_PASSWORD in .env to a private local value.
docker compose up --build -d
```

The API listens on port `8000`; PostgreSQL is available on port `5432`. The Codespaces configuration forwards ports `5173`, `5174`, and `8000`. The Compose password fallback is for local development only and must never be reused in a deployed environment.

The root `.env.example` documents Compose, Vite, cookie, CORS, and rate-limit settings. Generate and set a private staff MFA encryption key before staff onboarding:

```bash
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
# Put the generated value in STAFF_MFA_ENCRYPTION_KEY in the untracked root .env.
```

Back up this key securely; losing it prevents decrypting enrolled staff TOTP secrets. For production, configure `SESSION_COOKIE_SECURE=true`; use `SESSION_COOKIE_SAMESITE=none` only when the frontend and API are cross-site and both are HTTPS. The backend rejects production settings without secure session cookies.

Customer registration and sign-in use email one-time codes. Before using those flows, set `RESEND_API_KEY`, `EMAIL_FROM` (a sender verified with Resend), and a private random `OTP_HASH_SECRET` in the root `.env`; Compose passes these values to the API. For example, generate the OTP hash secret with `python -c 'import secrets; print(secrets.token_urlsafe(48))'`. Without a working email provider and hash secret, the API refuses to issue codes rather than simulating authentication.

### Frontend

```bash
npm install
npm run dev
```

The Vite development server proxies `/api/*` to `API_PROXY_TARGET` (default `http://localhost:8000`). Set `VITE_API_BASE_URL` to `/api/v1` for the local proxy or to the deployed API base URL, including `/api/v1`, for a separately hosted frontend. Configure that API's `CORS_ORIGINS` for the actual frontend origin; do not hardcode a Codespaces forwarding URL.

In development, the API also permits credentialed requests from the exact GitHub Codespaces forwarded frontend origins for ports `5173` and `5174`. This development-only allowlist is disabled in production, where `CORS_ORIGINS` must contain the exact deployed frontend origins.

### Staff operations application

The staff console is a separate app and uses the same API and PostgreSQL database:

```bash
cd admin
npm install
cp .env.example .env
npm run dev
```

Open `http://localhost:5174`. The admin app proxies API requests through its own Vite server; `admin/.env` only contains public frontend configuration, never server secrets. Customer sessions cannot authenticate to staff endpoints.

Create the first Owner only through the interactive backend bootstrap command after the database migration and MFA encryption key are configured:

```bash
docker compose up --build -d
docker compose exec -it api python -m scripts.bootstrap_owner
```

The command refuses if an Owner already exists, prompts for an Argon2id password, and requires the new Owner to verify authenticator TOTP before creating the account. Staff accounts are never created by public customer registration. Owners invite staff from the console; invitation tokens are one-time, expire after 48 hours, and must be delivered through an approved private channel (the app does not send email). Invitees set a password and enroll TOTP before activation. Staff login requires password plus a fresh TOTP code; staff sessions use separate HttpOnly cookies and an 8-hour default expiry.

Roles enforced by FastAPI include Owner, Super Admin, Operations Manager, Finance Manager, Customer Support, Inventory Officer, Agent Manager, and Auditor. The frontend hides inaccessible sections for usability, but each API endpoint independently checks permissions. Customer phone numbers are masked unless the role grants sensitive-data access. Customer status changes require a reason and revoke active customer sessions. Audit and order-event records are append-only in PostgreSQL.

The initial operations console includes a real-data overview, searchable/filterable/paginated order centre, customer lookup and account controls, staff invitations, audited catalogue management, support notes/escalations, and audit history. Staff permissions are read from relational role/permission tables and enforced by the API. Sample-catalogue orders are separated from business metrics. Requested order value is not described as revenue; verified revenue, margin, supplier, and inventory figures are unavailable until their evidence-backed ledgers and provider integrations exist.

Proposed production hosts `obia.com`, `admin.obia.com`, and `agents.obia.com` are deployment ideas only; no such domains or production setup are assumed. For a separately hosted admin/API pair, configure exact CORS origins, HTTPS, secure cookies, and `VITE_API_BASE_URL` for the admin API prefix `/api/v1/admin`.

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
| `POST` | `/api/v1/auth/register` | Register a customer and send an email-verification code |
| `POST` | `/api/v1/auth/login` | Verify credentials and send a sign-in code |
| `POST` | `/api/v1/auth/login/verify` | Verify the sign-in code and set an HttpOnly session cookie |
| `POST` | `/api/v1/auth/logout` | Revoke the current session (CSRF protected) |
| `GET` | `/api/v1/auth/me` | Return the authenticated customer's account |
| `GET` | `/api/v1/auth/csrf` | Issue/refresh a CSRF token for authenticated browser requests |
| `POST` | `/api/v1/auth/forgot-password` | Rate-limited; unavailable until a recovery provider is configured |
| `POST` | `/api/v1/auth/reset-password` | Rate-limited; unavailable until a verified reset-token workflow exists |
| `POST` | `/api/v1/auth/verify-phone` | Authenticated phone verification endpoint; unavailable without SMS integration |
| `POST` | `/api/v1/auth/resend-verification` | Authenticated request; unavailable without SMS integration |
| `POST` | `/api/v1/orders` | Create a purchase request (`Idempotency-Key` required) |
| `GET` | `/api/v1/orders/{reference}` | Retrieve order status using its unguessable reference |
| `GET` | `/api/v1/customers/me` | Authenticated customer profile |
| `GET` | `/api/v1/customers/me/orders` | Authenticated order history scoped to the session owner |
| `GET` | `/api/v1/admin/catalogue/networks` | Staff catalogue network list |
| `PATCH` | `/api/v1/admin/catalogue/networks/{network_id}/status` | Permission-checked network activation change with audit record |
| `GET` | `/api/v1/admin/catalogue/bundles` | Paginated staff catalogue bundle list |
| `PATCH` | `/api/v1/admin/catalogue/bundles/{bundle_id}` | Permission-checked bundle update with reason and revision history |
| `GET` | `/api/v1/admin/catalogue/bundles/{bundle_id}/history` | Bundle catalogue revision history |

Create a request with:

```json
{
  "phone": "+233 24 123 4567",
  "network_id": "mtn",
  "bundle_id": "mtn-sample-1gb"
}
```

The API validates Ghanaian mobile numbers with `phonenumbers`, normalizes them to E.164, validates catalogue IDs, creates/reuses a minimal customer record, and persists the new order as `pending_payment`. Send a fresh random `Idempotency-Key` header for each new purchase request and reuse it only when retrying that same request; the API stores a digest and rejects reuse for a different payload. Order references are generated with cryptographic randomness. Lookup results expose only a masked phone number. There is deliberately no public order-status mutation endpoint; state transitions are validated by the backend service. Database constraints also ensure an order's selected bundle belongs to its selected network and its amount is positive.

The initial Alembic migration seeds one clearly marked **sample-only** bundle per supported network at an illustrative amount. These are development fixtures, not verified offers, production prices, supplier inventory, or a promise to fulfill orders. The frontend labels sample offers/orders and does not claim that payment or delivery occurred.

## Customer accounts

Visit `/signup` to create an account with a full name, email address, Ghanaian phone number, and a password of at least 12 characters containing a letter and a number. The backend normalizes email and phone values and stores only an Argon2id password hash. Email must be verified before sign-in; phone remains unverified until an SMS provider is configured.

Sign in at `/login` with the verified email and password, then enter the one-time code sent by email. Authentication uses an opaque random session token; only its SHA-256 digest is stored in PostgreSQL. The browser receives a `HttpOnly` session cookie (7-day default); it is not placed in localStorage. A separate CSRF token is required for authenticated state-changing requests. Same-origin development uses the Vite API proxy. For separate production origins, allow only the frontend origin in `CORS_ORIGINS`, enable credentials, deploy over HTTPS, and set secure cookie options.

`/dashboard` is session-protected in the UI and on every private API endpoint. Customer order history is filtered by its authenticated account owner; pre-account/anonymous orders are not automatically attached to an account merely because the same phone number was entered during signup. An authenticated purchase request is owned by that session; recipient numbers can differ and are stored separately.

Registration and login are rate limited using database-backed per-IP windows (`AUTH_RATE_LIMIT`, `AUTH_RATE_WINDOW_SECONDS`), so limits are shared between API workers. The client address is taken from the direct ASGI connection; configure trusted proxy handling at the deployment boundary before running behind a proxy/load balancer.

## Checks

```bash
# Frontend
npm test
npm run build

# Independent administration frontend
npm --prefix admin install
npm --prefix admin run build

# Backend (from repository root)
cd backend
python -m pip install -r requirements.txt
python -m pytest -q
alembic upgrade head
```

Backend tests use an in-memory SQLite database. To verify PostgreSQL connectivity and migrations locally, start the Compose services and check `GET /api/v1/health`; the API container applies migrations on startup. PostgreSQL-specific append-only triggers are created by the admin operations migration.

## Known limitations and integration requirements

- Phone OTP delivery and verification are **unavailable** until an SMS provider is selected, configured, and verified. Accounts are explicitly marked phone-unverified; no OTP appears in responses or logs.
- Password recovery/reset returns an unavailable response until a real recovery provider and single-use reset-token workflow are integrated; the UI does not claim a recovery message was sent.
- The Stage 1 staff console does not yet include inventory, supplier, payment/finance/refund, agent, business-customer, alert, export, or configurable second-person approval workflows. Customer auth does not grant admin access.
- Customer and staff profiles now share a canonical `User` identity record, but there is no verified account-linking workflow. Existing customer and staff accounts were backfilled independently, without automatic merging; phone verification is unavailable until an SMS provider is configured.
- Staff onboarding requires a configured `STAFF_MFA_ENCRYPTION_KEY`; staff invitation delivery is manual. TOTP secret encryption depends on securely backing up this key.
- No payment provider, supplier API, verified payment ledger, revenue/profit basis, or stock ledger exists. The operations app correctly shows these metrics as unavailable instead of treating order requests as financial results.
- The default development cookie is non-Secure for localhost. Production requires HTTPS and `SESSION_COOKIE_SECURE=true`; select `SameSite` based on deployment topology.
- The Terms and Privacy pages are drafts; legal review and a production privacy/retention policy are launch requirements.
- The order starts at `pending_payment`. No payment attempt, payment confirmation, fulfillment request, or completion is fabricated; public callers cannot set status.
- Payment and mobile-data supplier providers are not selected or integrated. Before integration, obtain provider API documentation and sandbox access, commercial/licensing agreements, callback-signing and idempotency specifications, reconciliation/refund rules, and production credentials. Store real credentials in a managed secret store/environment, never in source control.
- Production pricing, catalogue validity, payment callbacks, supplier delivery confirmation, cancellation/refund automation, bot/WAF controls, trusted proxy configuration, and operational monitoring need to be designed and verified before launch.
- Bundle checkout currently creates a persisted purchase request only. It does not charge a customer or deliver mobile data.
