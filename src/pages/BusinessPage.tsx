import { useState } from "react";
import {
  DataState,
  Icon,
  NoticeBanner,
  PageIntro,
  StatusPill,
} from "../components/Ui";

const modules = [
  { id: "catalogue", label: "Catalogue", icon: "spark" as const },
  { id: "pricing", label: "Pricing & margins", icon: "wallet" as const },
  { id: "transactions", label: "Transactions", icon: "receipt" as const },
  { id: "reconciliation", label: "Reconciliation", icon: "refresh" as const },
  { id: "support", label: "Customer support", icon: "support" as const },
  { id: "reports", label: "Reports", icon: "chart" as const },
];

type ModuleId = (typeof modules)[number]["id"];

const moduleDetails: Record<ModuleId, { title: string; description: string }> = {
  catalogue: {
    title: "Catalogue management",
    description: "Manage supplier-approved bundles and monitor network availability.",
  },
  pricing: {
    title: "Pricing and margins",
    description: "Review supplier costs, retail prices, agent pricing, and margin inputs.",
  },
  transactions: {
    title: "Transaction monitoring",
    description: "Review payment, fulfillment, cancellation, and refund states.",
  },
  reconciliation: {
    title: "Reconciliation",
    description: "Compare verified payment and supplier records and investigate exceptions.",
  },
  support: {
    title: "Customer support",
    description: "Review customer enquiries and resolve order questions with a clear audit trail.",
  },
  reports: {
    title: "Reports and exports",
    description: "Explore operational and financial reporting once business data is connected.",
  },
};

const metrics = [
  ["Orders today", "Awaiting live order data"],
  ["Sales volume", "GHS —"],
  ["Pending delivery", "Awaiting supplier data"],
  ["Needs attention", "Awaiting reconciliation"],
];

const tableHeaders: Record<ModuleId, string[]> = {
  catalogue: ["Bundle", "Network", "Supplier", "Availability", "Retail price", "Action"],
  pricing: ["Bundle", "Supplier cost", "Retail price", "Agent price", "Margin", "Updated"],
  transactions: ["Order", "Network", "Amount", "Payment", "Delivery", "Created"],
  reconciliation: ["Reference", "Payment provider", "Supplier", "Difference", "Last checked", "State"],
  support: ["Case", "Customer", "Order reference", "Topic", "Opened", "Status"],
  reports: ["Report", "Period", "Last generated", "Format", "Status", "Action"],
};

export function BusinessPage() {
  const [activeModule, setActiveModule] = useState<ModuleId>("catalogue");
  const [connectionMessage, setConnectionMessage] = useState("");
  const details = moduleDetails[activeModule];

  function checkConnection() {
    setConnectionMessage("Business API is not configured in this preview. No request was sent.");
  }

  return (
    <main className="workspace-page business-page" id="main-content" tabIndex={-1}>
      <div className="workspace-container">
        <PageIntro
          eyebrow="PRIVATE BUSINESS WORKSPACE"
          title="Operations, all in one place."
          description="Manage the details behind reliable mobile data delivery—from catalogue to reconciliation."
          actions={
            <button className="button button--outline" onClick={checkConnection} type="button">
              <Icon name="refresh" size={16} />
              Check connection
            </button>
          }
        />

        <NoticeBanner title="Business workspace is not connected" tone="warning">
          This preview has no authenticated session or live business records. Actions are unavailable until role-based backend access is configured.
        </NoticeBanner>

        {connectionMessage && (
          <div className="connection-feedback" role="status">
            <Icon name="clock" size={16} />
            {connectionMessage}
            <button aria-label="Dismiss message" onClick={() => setConnectionMessage("")} type="button">
              <Icon name="close" size={15} />
            </button>
          </div>
        )}

        <section className="metric-grid metric-grid--business" aria-label="Business overview">
          {metrics.map(([label, note]) => (
            <article className="metric-card metric-card--business" key={label}>
              <span className="metric-card__label">{label}</span>
              <strong className="metric-card__value">—</strong>
              <span className="metric-card__note">{note}</span>
            </article>
          ))}
        </section>

        <section className="business-workspace" aria-label="Business operations">
          <nav className="business-nav" aria-label="Business sections">
            <span className="business-nav__label">WORKSPACE</span>
            {modules.map((module) => (
              <button
                aria-current={activeModule === module.id ? "page" : undefined}
                className={`business-nav__item${activeModule === module.id ? " is-active" : ""}`}
                key={module.id}
                onClick={() => {
                  setActiveModule(module.id);
                  setConnectionMessage("");
                }}
                type="button"
              >
                <Icon name={module.icon} size={17} />
                {module.label}
                {module.id === "reconciliation" && <span className="business-nav__dot" aria-label="Requires setup" />}
              </button>
            ))}
            <div className="business-nav__security">
              <Icon name="lock" size={15} />
              <span>Private workspace<br /><strong>Sign-in required</strong></span>
            </div>
          </nav>

          <div className="business-content">
            <div className="business-content__heading">
              <div>
                <span className="eyebrow">{modules.find((module) => module.id === activeModule)?.label.toUpperCase()}</span>
                <h2>{details.title}</h2>
                <p>{details.description}</p>
              </div>
              {activeModule === "catalogue" && (
                <button className="button button--primary" disabled type="button">
                  <Icon name="plus" size={16} />
                  Add bundle
                </button>
              )}
              {activeModule === "reports" && (
                <button className="button button--primary" disabled type="button">
                  <Icon name="arrow-down" size={16} />
                  Export report
                </button>
              )}
            </div>

            {activeModule === "pricing" && (
              <div className="pricing-summary">
                <div><span>Supplier cost</span><strong>Not connected</strong></div>
                <div><span>Retail price</span><strong>Not configured</strong></div>
                <div><span>Agent commission</span><strong>Policy pending</strong></div>
                <p>Prices, costs, and margins will only be editable after authorized access and supplier data are configured.</p>
              </div>
            )}

            <div className="business-table-wrap">
              <table className="business-table">
                <thead>
                  <tr>{tableHeaders[activeModule].map((header) => <th key={header} scope="col">{header}</th>)}</tr>
                </thead>
              </table>
              <DataState
                icon={activeModule === "reports" ? "chart" : activeModule === "support" ? "support" : "receipt"}
                title={`No ${activeModule === "reports" ? "reports" : activeModule === "support" ? "support cases" : activeModule} to show`}
              >
                Connect the authorized business API to load verified {activeModule} records. No sample transactions or prices are shown.
              </DataState>
            </div>

            <div className="business-content__footer">
              <span><Icon name="shield" size={15} /> Changes will be recorded in the business audit history.</span>
              <StatusPill tone="neutral">Integration required</StatusPill>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
