# Project Plan

**Status**: Planning
**Created**: 2026-11-05
**Mode**: NEW

---

## 1. Project Overview

**Goal**: Build Falaaa, a responsive Ghanaian marketplace for mobile data bundles on MTN, Telecel, and AirtelTigo (AT), serving retail customers and agents at launch. Customers discover bundles, pay in GHS, and track delivery; agents sell through the same marketplace; a private business dashboard controls catalogues, prices, margins, transactions, reconciliation, and support. This is a proposal: exact supplier/payment providers, API semantics, fees, volumes, launch date, and hosting region remain validation items. Every module is independently testable.

**App Type**: SPA + API

**API Login**: Yes

**Mode**: NEW

**Deployment Plan**: No deployment plan found

---

## 2. Purchase API — backend

| Component | Technology |
|-----------|-----------|
| **Language** | Python |
| **Runtime** | CPython |
| **Framework** | FastAPI |
| **Hosting** | Azure Container Apps |
| **Package Manager** | pip |
| **Test Runner** | pytest |
| **Mocking Library** | unittest.mock |
| **Test Command** | pytest |
| **Orchestration** | docker-compose |

Own the normalized bundle catalogue, GHS pricing and agent commissions, order/payment state machine, provider callbacks, reconciliation APIs, and audit events. Keep payment and bundle integrations behind separate provider adapters. Evaluate Hubtel or another licensed payment gateway and an approved supplier such as DT One, DingConnect, Reloadly, or another contracted provider; no provider is selected by this plan. Do not collect or store wallet PINs. Minimize and mask recipient phone data in business views. Record pricing changes, provider events, refunds, and operator actions in an auditable history.

## 3. Bundle Storefront — frontend

| Component | Technology |
|-----------|-----------|
| **Language** | TypeScript |
| **Framework** | React + Vite |
| **Package Manager** | npm |
| **Test Runner** | Vitest |
| **Mocking Library** | Vitest |
| **Test Command** | npm test |

Use a client-rendered SPA because the storefront and operations workspaces are interactive, authenticated application surfaces rather than content-led pages. Vite provides a small build and development toolchain without adding a server-rendering layer; React Router owns the `/`, `/orders`, `/agent`, and `/business` routes. Serve the built assets from static hosting and send `/api/*` requests to the separately deployed FastAPI service. This replaces the earlier Next.js proposal and does not change the Python API or worker runtimes.

Use lightweight, project-owned React components and CSS rather than Fluent UI: the required marketplace visual language is bespoke, and the app does not need a component-library dependency. Keep the storefront responsive on phones, tablets, and laptops; no native app at launch. Include network and bundle discovery, recipient entry, checkout, receipts, and purchase/refund status. Keep low-friction checkout while supporting customer purchase history. Until verified catalogue and payment APIs are integrated, show explicit unavailable/connection-required states instead of offers, prices, or successful transactions.

## 4. Fulfillment Worker — worker

| Component | Technology |
|-----------|-----------|
| **Language** | Python |
| **Runtime** | CPython |
| **Framework** | Azure Functions queue-triggered worker |
| **Package Manager** | pip |
| **Test Runner** | pytest |
| **Mocking Library** | unittest.mock |
| **Test Command** | pytest |
| **Orchestration** | docker-compose |

Dispatch only after the gateway confirms the payment state required by its transaction model. Use bounded retries and duplicate protection; reconcile payment and supplier states and confirm delivery only from verified supplier evidence. Unattended automation depends on verifying provider APIs, idempotency, callbacks, and refund capabilities. Until those checks pass, ambiguous outcomes go to an alerted exception queue rather than an unsafe retry or unsupported refund. Implement a supplier-independent adapter boundary, but begin with one verified supplier route per supported network. Referrals and advanced supplier routing are later-phase only.

## 5. Services Required

| Azure Service | Role in App | Environment Variable | Default Value (Local) | Classification |
|---------------|------------|----------------------|-----------------------|----------------|
| Azure Container Apps | Host the FastAPI API | `PORT` / `API_BASE_URL` | `8000` / `http://localhost:8000` | Essential |
| Static web hosting | Serve the built React + Vite storefront and route API requests to the API service | `API_BASE_URL` | `/api` (local development proxy) | Essential |
| Azure Functions | Run queue-triggered fulfillment and reconciliation work | `AzureWebJobsStorage` | `UseDevelopmentStorage=true` | Essential |
| PostgreSQL Flexible Server | Store catalogue, orders, payment state, agent settings, prices, commissions, and audit records | `DATABASE_URL` | `postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/falaaa` | Essential |
| Azure Queue Storage | Durable asynchronous fulfillment and exception work | `STORAGE_CONNECTION_STRING` | `UseDevelopmentStorage=true` | Essential |
| Azure Blob Storage | Azure Functions host storage; optional report/export artifacts | `STORAGE_CONNECTION_STRING` | `UseDevelopmentStorage=true` | Essential |
| Azure Key Vault | Store gateway and supplier credentials; workloads access Azure resources using managed identity | `KEY_VAULT_URI` | Not required locally; use local development secrets | Essential |
| Azure Monitor / Application Insights | Operational telemetry and alerting; business audit history remains in PostgreSQL | `APPLICATIONINSIGHTS_CONNECTION_STRING` | Optional | Enhancement |

External essentials: one licensed payment API and one approved bundle supplier API for each launch network, subject to contract and capability validation. Do not treat any named candidate as selected or assume common callback, idempotency, status, or refund semantics across providers.

## 6. Prerequisites

Verify every `❓` item before local debugging or scaffold execution; this environment could not confirm installation. The local Python version is detected, but the worker's supported Functions/Python runtime pairing must be confirmed during setup.

### Run

| Tool | Service(s) | Installed | Version |
|------|------------|-----------|---------|
| Node.js | storefront | ✅ | v24.22.2 |
| npm | storefront | ✅ | 11.19.1 |
| Python | purchase-api, fulfillment-worker | ✅ | 3.14.2 |
| pip | purchase-api, fulfillment-worker | ✅ | 26.2.2 |
| Azure Functions Core Tools | fulfillment-worker | ❓ | — |

### Debug

| Tool | Service(s) | Installed | Version |
|------|------------|-----------|---------|
| Docker | purchase-api, fulfillment-worker | ✅ | 29.9.2-2 (engine responds) |
| Docker Compose | purchase-api, fulfillment-worker | ✅ | v5.6.1 |
| Chrome | storefront | ❓ | — (Linux browser fallback; verify before browser debugging) |
| `ms-azuretools.vscode-azurefunctions` | fulfillment-worker | ❓ | — |

## 7. Design System & UI

**Component Library**: Project-owned React components and CSS; no UI library
**Style Direction**: A crisp, transaction-first Ghanaian connectivity marketplace: bright, high-contrast surfaces for fast bundle comparison, with a restrained green brand anchor and warm gold/coral status accents. Keep operational tables compact and expose price, cost, margin, and transaction state without decorative clutter.
**Typography**: Aptos with system sans-serif fallbacks; use tabular figures for GHS amounts and transaction identifiers.

### Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `primary` | `#0B684B` | Falaaa actions, selected networks, and active navigation |
| `accent` | `#E5A72F` | Agent and pricing highlights; attention states |
| `surface` | `#F4F7F4` | Storefront and operations workspace background |
| `text` | `#17251F` | Bundle names, amounts, and operational data |
| `muted` | `#63736A` | Provider-validation notes, timestamps, and secondary labels |
| `border` | `#D6E0D9` | Catalogue rows, inputs, and dashboard dividers |

### Pages

| Page | Route | Purpose | Layout |
|------|-------|---------|--------|
| Bundle Catalog | `/` | Browse Ghana launch networks and their verified offers; show no price until supplier catalogue and rate data are confirmed. | `header + nav + hero + grid + footer` |
| Customer Orders | `/orders` | View purchase, delivery, cancellation, and refund status with receipts. | `header + nav + main + table + footer` |
| Agent Workbench | `/agent` | Start an agent-assisted sale and review agent transaction/commission status. | `header + nav + hero + main + empty + footer` |
| Business Dashboard | `/business` | Private controls for orders, customers, agents, suppliers, balances, pricing, margins, reconciliation, and reports. | `header + nav + main + kpi-row + error (inline banner) + table + footer` |

### Sample Content

Preview records below are illustrative UI fixtures only. They are not live catalogue, provider states, prices, commissions, fees, or volume forecasts.

Bundle Catalog — launch network:
| Network | Catalogue | Retail price |
|---------|-----------|--------------|
| MTN | Supplier validation pending | GHS — |
| Telecel | Supplier validation pending | GHS — |
| AirtelTigo (AT) | Supplier validation pending | GHS — |

Customer Orders — example state fixture:
| Reference | Network | Amount | State |
|-----------|---------|--------|-------|
| FLA-TEST-001 | MTN | GHS — | Awaiting payment confirmation |
| FLA-TEST-002 | Telecel | GHS — | Awaiting delivery confirmation |
| FLA-TEST-003 | AirtelTigo (AT) | GHS — | Refund eligibility review |

Agent Workbench — first-release workflow:
| Workflow | Price/commission | State |
|----------|------------------|-------|
| Customer bundle sale | GHS — / pending configuration | Ready for provider validation |
| Agent bundle sale | GHS — / pending configuration | Agent workflow in MVP |
| Commission adjustment | Pending policy | Audit review required |

Business Dashboard — operational queue:
| Record | Network | Amount | State |
|--------|---------|--------|-------|
| FLA-TEST-001 | MTN | GHS — | Reconciliation pending |
| FLA-TEST-002 | Telecel | GHS — | Supplier confirmation pending |
| FLA-TEST-003 | AirtelTigo (AT) | GHS — | Refund capability validation |

## 8. Project Structure

```text
falaaa/
├── .azure/
│   ├── project-plan.md
│   └── .preview-temp/
├── apps/
│   └── storefront/                 # React + Vite + TypeScript SPA
├── services/
│   ├── purchase-api/               # FastAPI routes, domain services, adapters
│   │   ├── app/api/
│   │   ├── app/domain/
│   │   ├── app/providers/           # payment and supplier contracts/adapters
│   │   ├── app/persistence/
│   │   └── tests/
│   └── fulfillment-worker/         # Azure Functions queue handlers
│       ├── functions/
│       ├── app/providers/
│       └── tests/
├── migrations/                     # PostgreSQL schema migrations
├── contracts/                      # shared API and provider-neutral schemas
├── infra/                          # added after plan approval
├── compose.yaml
└── .env.example
```

## 9. Route Definitions

| # | Method | Path | Description | Request Body | Response Body | Status Codes |
|---|--------|------|-------------|-------------|--------------|-------------|
| 1 | GET | `/api/health` | Health check | — | `{status, services}` | 200, 503 |
| 2 | GET | `/api/v1/bundles` | List normalized offers by network; return only validated price/availability | Query: `network` | `{offers: [...]}` | 200, 503 |
| 3 | POST | `/api/v1/orders` | Create purchase intent with internal duplicate protection | `{network, offerId, recipient, channel}` | `{orderId, paymentStatus}` | 201, 409, 422 |
| 4 | POST | `/api/v1/orders/{orderId}/payments` | Start payment using configured licensed gateway | `{paymentMethod, returnUrl?}` | `{paymentReference, status, nextAction?}` | 200, 409, 422, 502 |
| 5 | GET | `/api/v1/orders/{orderId}` | Read purchase, delivery, and refund status | — | `{order, payment, fulfillment, receipt}` | 200, 404 |
| 6 | POST | `/api/v1/webhooks/payments/{provider}` | Process verified payment callback per provider contract | Provider-defined; validate before integration | `{accepted}` | 200, 400, 409 |
| 7 | POST | `/api/v1/webhooks/suppliers/{provider}` | Process supplier delivery/status callback where supported | Provider-defined; validate before integration | `{accepted}` | 200, 400, 409 |
| 8 | GET | `/api/v1/agents/transactions` | List agent sales and commission state | Query: filters/cursor | `{items, nextCursor}` | 200, 422 |
| 9 | GET | `/api/v1/business/orders` | Operations order and reconciliation queue | Query: status/network/cursor | `{items, nextCursor}` | 200, 422 |
| 10 | PATCH | `/api/v1/business/pricing/{offerId}` | Update retail/agent price and margin inputs with audit event | `{retailPrice, agentPrice?, commission?}` | `{offer, auditEventId}` | 200, 404, 409, 422 |
| 11 | POST | `/api/v1/business/orders/{orderId}/refunds` | Request refund; execute automatically only if gateway and order state permit | `{reason}` | `{refundStatus, providerReference?}` | 202, 409, 422, 502 |

## 10. Next Steps

1. Review and approve this plan; approval starts the scaffold workflow, not production provider automation.
2. Before unattended fulfillment is enabled, verify supplier/payment API identities and contracts, sandbox behavior, idempotency, callback authentication and delivery semantics, reconciliation source of truth, and refund support/rules.
3. Confirm expected average/peak volume, launch date, exact fees/taxes/commission policy, licensing/compliance/support requirements, and hosting region; do not encode guesses as defaults.
4. Scaffold the app and provider-neutral contracts, then integrate only the confirmed provider adapters and test duplicate, timeout, callback, reconciliation, and refund paths.
