import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { DataState, Icon, NoticeBanner, PageIntro } from "../components/Ui";

type OrderFilter = "all" | "in-progress" | "complete";

export function OrdersPage() {
  const [reference, setReference] = useState("");
  const [filter, setFilter] = useState<OrderFilter>("all");
  const [message, setMessage] = useState("");

  function handleTrack(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(
      reference.trim()
        ? "Order tracking is not connected yet. No lookup was sent and no order status has been retrieved."
        : "Enter an order reference to check its status once tracking is connected.",
    );
  }

  return (
    <main className="workspace-page" id="main-content" tabIndex={-1}>
      <div className="workspace-container">
        <PageIntro
          eyebrow="YOUR FALAAA ACCOUNT"
          title="Orders, without the guesswork."
          description="Look up an order by reference or review your recent activity in one place."
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
                setMessage("");
              }}
              placeholder="e.g. FLA-123456"
              value={reference}
            />
            <button className="button button--primary" type="submit">
              Track order
              <Icon name="arrow-right" size={16} />
            </button>
          </form>
          {message && <p className="form-feedback" role="status">{message}</p>}
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
            <span className="history-toolbar__hint">No customer history is stored in this preview.</span>
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
            <DataState icon="receipt" title="Your orders will appear here">
              {filter === "all"
                ? "Once connected, you’ll find receipts and clear payment and delivery updates here."
                : `There are no ${filter === "complete" ? "completed" : "in-progress"} orders to show in this preview.`}
            </DataState>
          </div>
        </section>

        <NoticeBanner title="Order updates are not connected">
          Payment, delivery, cancellation, and refund statuses will be retrieved from the backend when order tracking is available.
        </NoticeBanner>
      </div>
    </main>
  );
}
