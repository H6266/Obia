import { Link } from "react-router-dom";
import { OrderComposer } from "../components/OrderComposer";
import {
  DataState,
  Icon,
  NoticeBanner,
  PageIntro,
  StatusPill,
} from "../components/Ui";

const agentStats = [
  { label: "Sales today", value: "—", note: "Requires transaction data", icon: "wallet" as const },
  { label: "Commission", value: "—", note: "Policy not configured", icon: "spark" as const },
  { label: "Agent balance", value: "—", note: "Balance service required", icon: "shield" as const },
];

export function AgentPage() {
  return (
    <main className="workspace-page" id="main-content" tabIndex={-1}>
      <div className="workspace-container">
        <PageIntro
          eyebrow="FALAAA FOR AGENTS"
          title="Your workday, made simpler."
          description="Start a customer sale, keep every detail in view, and stay on top of order status."
          actions={
            <Link className="button button--outline" to="/orders">
              View customer orders
              <Icon name="arrow-up-right" size={16} />
            </Link>
          }
        />

        <NoticeBanner title="Agent tools are in preview">
          Sales, balances, pricing, and commissions are not connected to an account or provider service.
        </NoticeBanner>

        <section className="metric-grid" aria-label="Agent overview">
          {agentStats.map((stat) => (
            <article className="metric-card" key={stat.label}>
              <span className="metric-card__icon"><Icon name={stat.icon} size={19} /></span>
              <span className="metric-card__label">{stat.label}</span>
              <strong className="metric-card__value">{stat.value}</strong>
              <span className="metric-card__note">{stat.note}</span>
            </article>
          ))}
        </section>

        <div className="agent-workspace-grid">
          <OrderComposer agentMode />
          <aside className="agent-aside">
            <section className="panel-card agent-checklist">
              <div className="panel-card__heading">
                <div><span className="eyebrow">A QUICK CHECK</span><h2>Before you confirm</h2></div>
                <span className="panel-card__heading-icon"><Icon name="check" size={19} /></span>
              </div>
              <ol>
                <li><span>1</span><div><strong>Confirm the network</strong><p>Match the bundle to the recipient’s network.</p></div></li>
                <li><span>2</span><div><strong>Check the phone number</strong><p>Read the number back before payment.</p></div></li>
                <li><span>3</span><div><strong>Wait for confirmation</strong><p>Only share a completed status after it is verified.</p></div></li>
              </ol>
            </section>
            <section className="agent-help-card">
              <span className="agent-help-card__icon"><Icon name="support" size={19} /></span>
              <h3>Need help with a sale?</h3>
              <p>Support contact details will appear here when the agent programme launches.</p>
              <span className="agent-help-card__status"><StatusPill tone="neutral">Support setup pending</StatusPill></span>
            </section>
          </aside>
        </div>

        <section className="history-section" aria-labelledby="agent-sales-title">
          <div className="section-heading section-heading--compact">
            <div>
              <span className="eyebrow">RECENT ACTIVITY</span>
              <h2 id="agent-sales-title">Your latest sales</h2>
            </div>
            <span className="demo-label"><span /> Live data not connected</span>
          </div>
          <div className="history-table-wrap">
            <table className="history-table">
              <thead>
                <tr>
                  <th scope="col">Reference</th>
                  <th scope="col">Recipient</th>
                  <th scope="col">Bundle</th>
                  <th scope="col">Commission</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
            </table>
            <DataState icon="receipt" title="No sales to show yet">
              Completed and pending sales will appear here after the agent account is connected.
            </DataState>
          </div>
        </section>
      </div>
    </main>
  );
}
