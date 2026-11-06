# Falaaa contributor instructions

- Keep the customer app in React + TypeScript + Vite. Preserve existing routes, components, accessibility, and responsive styling.
- Keep backend code in `backend/app/`; separate FastAPI routes, Pydantic schemas, SQLAlchemy models, configuration, and service logic. Do not accumulate backend behavior in `main.py`.
- Use Alembic for schema changes. Add a new migration rather than editing a migration that may already have been applied.
- Treat PostgreSQL as the application database. Use the SQLite test fixture for API tests, and verify database migrations against PostgreSQL when available.
- Keep catalogue fixtures and prices visibly identified as samples. Never imply that a sample offer is live or can be fulfilled.
- Validate Ghanaian phone numbers with `phonenumbers`; normalize stored values to E.164 and expose only masked numbers in order responses.
- Keep orders `pending_payment` until a verified payment event exists. Route all state changes through `app/services/order_service.py`; never expose public status mutation or fulfillment actions.
- Do not add pretend OTP, payment, supplier, or admin authorization. Customer history and admin operations require a real identity/authorization provider before exposure.
- Keep secrets in environment configuration or a managed secret store. Never commit `.env` files, API keys, payment PINs, passwords, or OTPs.
- Frontend API calls belong in `src/lib/api.ts`. Use `VITE_API_BASE_URL` for the API base and the configurable Vite proxy for local development; do not hardcode Codespaces forwarding URLs.
- Surface loading, API error, and unverified/sample states in the UI; do not show success unless the backend confirms the request.

## Validation

```bash
npm test
npm run build

cd backend
python -m pytest -q
alembic upgrade head
```

For PostgreSQL-backed local development, use `docker compose up --build -d`. The API container runs migrations before startup.
