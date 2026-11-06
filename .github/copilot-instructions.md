# Falaaa contributor instructions

- Keep the customer app in React + TypeScript + Vite. Preserve existing routes, components, accessibility, and responsive styling.
- Keep backend code in `backend/app/`; separate FastAPI routes, Pydantic schemas, SQLAlchemy models, configuration, and service logic. Do not accumulate backend behavior in `main.py`.
- Use Alembic for schema changes. Add a new migration rather than editing a migration that may already have been applied.
- Treat PostgreSQL as the application database. Use the SQLite test fixture for API tests, and verify database migrations against PostgreSQL when available.
- Use `User` as the shared credential/account principal for customer and staff profiles. Keep profile records distinct, never auto-merge existing identities, and do not claim account linking until both accounts can be verified.
- Keep catalogue fixtures and prices visibly identified as samples. Never imply that a sample offer is live or can be fulfilled.
- Validate Ghanaian phone numbers with `phonenumbers`; normalize stored values to E.164 and expose only masked numbers in order responses.
- Keep orders `pending_payment` until a verified payment event exists. Route all state changes through `app/services/order_service.py`; never expose public status mutation or fulfillment actions.
- Customer sessions use opaque HttpOnly cookies and CSRF validation; keep protected API routes protected server-side. Do not treat customer role as administrative authorization.
- Keep the operations console in the separate `admin/` React/Vite app; it must use the existing API/database and must not duplicate business rules or customer authentication.
- Staff accounts are invitation-only, use separate HttpOnly sessions, mandatory TOTP MFA, encrypted MFA secrets, and server-enforced role permissions. Create the initial Owner only with `backend/scripts/bootstrap_owner.py`; never add public staff/Owner registration.
- Resolve staff authorization from the database-backed role, permission, and role-permission tables; frontend visibility is never authorization.
- Require a fresh random `Idempotency-Key` for each purchase request and reuse it only for retries of the same payload. Keep only a digest/fingerprint in storage and preserve the order's historical amount snapshot.
- Route staff catalogue changes through the catalogue service so each accepted update is transactional, audited, and recorded in append-only revision history.
- Preserve database order integrity: the selected bundle must belong to the selected network, and order amounts must be positive.
- Audit and order-event records are append-only in PostgreSQL. Record administrative changes and sensitive data access, and do not add mutation endpoints for payment or fulfilment state without verified provider evidence.
- Do not infer revenue, profit, supplier balances, or inventory from order requests. Keep unavailable metrics explicitly unavailable; exclude sample catalogue records from business metrics.
- Argon2id hashes are the only stored passwords. Never store session tokens in the browser's localStorage or log passwords, cookies, CSRF tokens, or OTPs.
- Do not simulate SMS, password recovery, payment, supplier delivery, or admin authorization. Mark phone accounts unverified and expose provider-dependent operations as unavailable until a real provider exists.
- Keep account ownership distinct from recipient phone numbers. Customer order history must query the authenticated account owner and must not expose legacy guest orders.
- Apply rate limits to registration, login, recovery, and verification endpoints; keep them shared across API workers (the current database-backed limit buckets are deliberate).
- Keep secrets in environment configuration or a managed secret store. Never commit `.env` files, API keys, payment PINs, passwords, or OTPs.
- Frontend API calls belong in `src/lib/api.ts`. Use `VITE_API_BASE_URL` for the API base and the configurable Vite proxy for local development; do not hardcode Codespaces forwarding URLs.
- Surface loading, API error, and unverified/sample states in the UI; do not show success unless the backend confirms the request.

## Validation

```bash
npm test
npm run build
npm --prefix admin run build

cd backend
python -m pytest -q
alembic upgrade head
```

For PostgreSQL-backed local development, use `docker compose up --build -d`. The API container runs migrations before startup.
