import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { DataState, Icon, NoticeBanner, PageIntro } from "../components/Ui";
import { getOrder, type PurchaseOrder } from "../lib/api";

type OrderFilter = "all" | "in-progress" | "complete";

export function OrdersPage() {
  const [reference, setReference] = useState("");
  const [filter, setFilter] = useState<OrderFilter>("all");
  const [order, setOrder] = useState<PurchaseOrder | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleTrack(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!reference.trim()) {
      setError("Enter an order reference.");
      setOrder(null);
      return;
    }

    setLoading(true);
    setError("");
    setOrder(null);
    try {
      setOrder(await getOrder(reference));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not retrieve this order.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="workspace-page" id="main-content" tabIndex={-1}>
      <div className="workspace-container">
        <PageIntro
          eyebrow="YOUR FALAAA ACCOUNT"
          title="Orders, without the guesswork."
          description="Look up an order by reference. Customer order history will be available after secure sign-in is integrated."
          actions={
            <Link className="button button--primary" to="/">
              Buy data
              <Icon name="arrow-right" size={17} />
            </Link>
          }
        />

        <section className="tracking-card" aria-labelledby="tracking-title">
          <div className="tracking-card__copy">
            <span className="tracking-card__icon"><Icon name="search" size={21} /></span>
            <div>
              <h2 id="tracking-title">Track an order</h2>
              <p>Use the reference from your receipt. You do not need to enter your mobile money PIN.</p>
            </div>
          </div>
          <form className="tracking-form" onSubmit={handleTrack}>
            <label className="sr-only" htmlFor="order-reference">Order reference</label>
            <input
              autoComplete="off"
              id="order-reference"
              onChange={(event) => {
                setReference(event.target.value);
                setError("");
                setOrder(null);
              }}
              placeholder="e.g. FLA-123456"
              value={reference}
            />
            <button className="button button--primary" disabled={loading} type="submit">
              {loading ? "Looking up…" : "Track order"}
              <Icon name="arrow-right" size={16} />
            </button>
          </form>
          {error && <p className="form-feedback field-hint--error" role="alert">{error}</p>}
          {order && (
            <div className="order-lookup-result" aria-live="polite">
              <div>
                <span className="eyebrow">ORDER {order.reference}</span>
                <strong>{order.network} · {order.bundle}</strong>
                <span>Recipient {order.customer_phone}</span>
              </div>
              <div className="order-lookup-result__state">
                <strong>GHS {Number(order.amount).toFixed(2)} {order.currency}</strong>
                <span>Status: {order.status.replaceAll("_", " ")}</span>
              </div>
              {order.is_sample && (
                <p>Sample order only. No payment or delivery has been initiated.</p>
              )}
            </div>
          )}
        </section>

        <section className="history-section" aria-labelledby="history-title">
          <div className="section-heading section-heading--compact">
            <div>
              <span className="eyebrow">ORDER HISTORY</span>
              <h2 id="history-title">Your recent orders</h2>
            </div>
            <span className="demo-label"><span /> Account connection required</span>
          </div>

          <div className="history-toolbar">
            <div className="filter-tabs filter-tabs--small" role="group" aria-label="Filter order history">
              {([
                ["all", "All orders"],
                ["in-progress", "In progress"],
                ["complete", "Complete"],
              ] as const).map(([id, label]) => (
                <button
                  aria-pressed={filter === id}
                  className={filter === id ? "is-active" : ""}
                  key={id}
                  onClick={() => setFilter(id)}
                  type="button"
                >
                  {label}
                </button>
              ))}
            </div>
            <span className="history-toolbar__hint">History requires secure customer sign-in.</span>
          </div>

          <div className="history-table-wrap">
            <table className="history-table">
              <thead>
                <tr>
                  <th scope="col">Order</th>
                  <th scope="col">Network</th>
                  <th scope="col">Recipient</th>
                  <th scope="col">Total</th>
                  <th scope="col">Status</th>
                  <th scope="col"><span className="sr-only">Details</span></th>
                </tr>
              </thead>
            </table>
            <DataState icon="receipt" title="Sign-in is required for order history">
              {filter === "all"
                ? "Order history requires customer sign-in, which is not configured. You can still look up an order by its private reference above."
                : `Customer sign-in is required to show ${filter === "complete" ? "completed" : "in-progress"} order history.`}
            </DataState>
          </div>
        </section>

        <NoticeBanner title="Payment and delivery are not connected">
          The current backend can return an order’s recorded status. Payment confirmation, supplier fulfillment, cancellation, and refunds require verified provider integrations.
        </NoticeBanner>
      </div>
    </main>
  );
}
