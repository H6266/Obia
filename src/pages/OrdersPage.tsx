import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { DataState, Icon, NoticeBanner, PageIntro } from "../components/Ui";
import { getCustomerOrders, getOrder, type PurchaseOrder } from "../lib/api";

type OrderFilter = "all" | "in-progress" | "complete";

export function OrdersPage() {
  const [searchParams] = useSearchParams();
  const { customer, loading: authLoading } = useAuth();
  const [reference, setReference] = useState(searchParams.get("reference") ?? "");
  const [filter, setFilter] = useState<OrderFilter>("all");
  const [order, setOrder] = useState<PurchaseOrder | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<PurchaseOrder[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const initialReference = searchParams.get("reference");

  useEffect(() => {
    if (authLoading || !customer) {
      setHistory([]);
      return;
    }
    let active = true;
    setHistoryLoading(true);
    setHistoryError("");
    getCustomerOrders()
      .then((orders) => {
        if (active) setHistory(orders);
      })
      .catch((requestError: unknown) => {
        if (active) {
          setHistoryError(
            requestError instanceof Error ? requestError.message : "Could not load order history.",
          );
        }
      })
      .finally(() => {
        if (active) setHistoryLoading(false);
      });
    return () => {
      active = false;
    };
  }, [authLoading, customer]);

  useEffect(() => {
    if (!initialReference) return;
    setReference(initialReference);
    void trackOrder(initialReference);
  }, [initialReference]);

  const visibleHistory = history.filter((item) => {
    if (filter === "complete") return item.status === "completed";
    if (filter === "in-progress") {
      return !["completed", "failed", "cancelled", "refunded"].includes(item.status);
    }
    return true;
  });

  async function trackOrder(orderReference: string) {
    if (!orderReference.trim()) {
      setError("Enter an order reference.");
      setOrder(null);
      return;
    }

    setLoading(true);
    setError("");
    setOrder(null);
    try {
      setOrder(await getOrder(orderReference));
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

  function handleTrack(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void trackOrder(reference);
  }

  return (
    <main className="workspace-page" id="main-content" tabIndex={-1}>
      <div className="workspace-container">
        <PageIntro
          eyebrow="YOUR FALAAA ACCOUNT"
          title="Orders, without the guesswork."
          description="Look up any order by reference, or review orders linked to your signed-in account."
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
            <span className="demo-label"><span /> {customer ? "Account orders" : "Sign in to view history"}</span>
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
            <span className="history-toolbar__hint">
              {customer ? "Showing orders linked to your account." : "Sign in to see your account history."}
            </span>
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
              {visibleHistory.length > 0 && (
                <tbody>
                  {visibleHistory.map((item) => (
                    <tr key={item.reference}>
                      <td>{item.reference}</td>
                      <td>{item.network}</td>
                      <td>{item.customer_phone}</td>
                      <td>GHS {Number(item.amount).toFixed(2)}</td>
                      <td>{item.status.replaceAll("_", " ")}</td>
                      <td>
                        <button
                          className="text-button"
                          onClick={() => {
                            setReference(item.reference);
                            void trackOrder(item.reference);
                          }}
                          type="button"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              )}
            </table>
            {historyLoading ? (
              <div className="account-loading" role="status">Loading your order history…</div>
            ) : historyError ? (
              <p className="account-error" role="alert">{historyError}</p>
            ) : visibleHistory.length === 0 ? (
              <DataState icon="receipt" title={customer ? "No matching orders" : "Sign in for order history"}>
                {customer
                  ? `There are no ${filter === "all" ? "" : `${filter === "complete" ? "completed" : "in-progress"} `}orders in this view.`
                  : <>You can still track an order by reference above, or <Link to="/login">sign in</Link> to view your account history.</>}
              </DataState>
            ) : null}
          </div>
        </section>

        <NoticeBanner title="Payment and delivery are not connected">
          The current backend can return an order’s recorded status. Payment confirmation, supplier fulfillment, cancellation, and refunds require verified provider integrations.
        </NoticeBanner>
      </div>
    </main>
  );
}
