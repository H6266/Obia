# Falaaa

Falaaa is a responsive Ghanaian mobile-data marketplace frontend for MTN, Telecel, and AirtelTigo. This repository currently contains the customer storefront, order tracking view, agent workbench, and business operations dashboard; provider APIs and authentication are not connected.

## Frontend architecture

- **React + TypeScript + Vite** for a fast, client-rendered application.
- **React Router** for `/`, `/orders`, `/agent`, and `/business`.
- **Project-owned components and CSS** for a lightweight, accessible design system.
- The planned **Python + FastAPI** purchase API and Python fulfillment worker remain separate services. The storefront must not contain provider credentials or claim an order succeeded without a verified backend response.

Vite was selected over the earlier Next.js proposal because this product is an interactive storefront and operations SPA, not a content-led site. It avoids adding a server-rendering layer and keeps the browser app independent from the Python API. The technology decision is recorded in [.azure/project-plan.md](./.azure/project-plan.md) and [.azure/requirements.json](./.azure/requirements.json).

## Run locally

```bash
npm install
npm run dev
```

The interface is an integration-ready product demonstration. Catalogue offers, prices, authentication, payment, orders, reporting, and transaction actions remain explicitly unavailable until connected to verified services.

## Checks

```bash
npm test
npm run build
```

No mobile-money PIN is requested or stored. Customer phone numbers are only held in the current page state while composing a purchase.
