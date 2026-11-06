import { useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { api } from "../services/api";
import type { AdminOrder, OrderDetail, Page } from "../types";

export function OrdersPage() {
  const { staff } = useAuth();
  const [searchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("search") ?? "");
  const [status, setStatus] = useState(searchParams.get("status") ?? "");
  const [networkId, setNetworkId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortDirection, setSortDirection] = useState("desc");
  const [data, setData] = useState<Page<AdminOrder> | null>(null);
  const [selected, setSelected] = useState<OrderDetail | null>(null);
  const [note, setNote] = useState("");
  const [escalation, setEscalation] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);

  async function loadOrders(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ page: String(page), page_size: "25" });
      if (search.trim()) params.set("search", search.trim());
      if (status) params.set("status", status);
      if (networkId) params.set("network_id", networkId);
      if (startDate) params.set("start_date", startDate);
      if (endDate) params.set("end_date", endDate);
      params.set("sort_by", sortBy);
      params.set("sort_direction", sortDirection);
      setData(await api.orders(params));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not load orders.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadOrders();   }, [page, status, networkId, startDate, endDate, sortBy, sortDirection]);

  async function openOrder(reference: string) {
    setError("");
    setSelected(null);
    try {
      setSelected(await api.order(reference));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not load order details.");
    }
  }

  async function submitNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected || !note.trim()) return;
    setLoading(true);
    try {
      await api.addOrderNote(selected.reference, note.trim());
      setNote("");
      await openOrder(selected.reference);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not save support note.");
    } finally {
      setLoading(false);
    }
  }

  async function submitEscalation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected || !escalation.trim()) return;
    setLoading(true);
    try {
      await api.escalateOrder(selected.reference, escalation.trim());
      setEscalation("");
      await openOrder(selected.reference);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not escalate order.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <header className="page-heading"><div><span className="kicker">OPERATIONS</span><h1>Order centre</h1>
        <p>Search orders, review their recorded state, add support notes, and create escalations. Payment and delivery are never manually asserted here.</p></div></header>
      <form className="toolbar" onSubmit={(event) => { setPage(1); void loadOrders(event); }}>
        <label>Reference or customer phone
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Order reference" />
        </label>
        <label>Order status
          <select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}>
            <option value="">All statuses</option>
            {["pending_payment", "payment_processing", "paid", "fulfillment_pending", "processing", "completed", "failed", "cancelled", "refunded"].map((item) => <option key={item} value={item}>{item.replaceAll("_", " ")}</option>)}
          </select>
        </label>
        <label>Network<select value={networkId} onChange={(event) => { setNetworkId(event.target.value); setPage(1); }}>
          <option value="">All networks</option><option value="mtn">MTN</option><option value="telecel">Telecel</option><option value="at">AirtelTigo</option>
        </select></label>
        <label>From<input type="date" value={startDate} onChange={(event) => { setStartDate(event.target.value); setPage(1); }} /></label>
        <label>To<input type="date" value={endDate} onChange={(event) => { setEndDate(event.target.value); setPage(1); }} /></label>
        <label>Sort<select value={`${sortBy}:${sortDirection}`} onChange={(event) => {
          const [nextBy, nextDirection] = event.target.value.split(":");
          setSortBy(nextBy ?? "created_at"); setSortDirection(nextDirection ?? "desc");
        }}>
          <option value="created_at:desc">Newest first</option><option value="created_at:asc">Oldest first</option>
          <option value="amount:desc">Amount high to low</option><option value="amount:asc">Amount low to high</option>
          <option value="reference:asc">Reference A–Z</option><option value="reference:desc">Reference Z–A</option>
        </select></label>
        <button disabled={loading} type="submit">{loading ? "Searching…" : "Search"}</button>
      </form>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="table-scroll">
        <table>
          <thead><tr><th>Reference</th><th>Customer / recipient</th><th>Network · bundle</th><th>Amount</th><th>Order</th><th>Payment</th><th>Fulfilment</th><th>Created</th><th /></tr></thead>
          <tbody>
            {data?.items.map((order) => (
              <tr key={order.reference}>
                <td><strong>{order.reference}</strong>{order.is_sample && <small className="tag">Sample</small>}</td>
                <td>{order.customer_name || "Guest"}<small>{order.customer_phone} / {order.recipient_phone}</small></td>
                <td>{order.network}<small>{order.bundle}</small></td>
                <td>{order.currency} {Number(order.amount).toFixed(2)}</td>
                <td>{order.order_status.replaceAll("_", " ")}</td>
                <td>{order.payment_status.replaceAll("_", " ")}</td>
                <td>{order.fulfillment_status.replaceAll("_", " ")}</td>
                <td>{new Date(order.created_at).toLocaleString()}</td>
                <td><button className="button-secondary" type="button" onClick={() => void openOrder(order.reference)}>Details</button></td>
              </tr>
            ))}
            {!data?.items.length && <tr><td colSpan={9} className="empty-cell">{loading ? "Loading orders…" : "No matching orders."}</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="pagination">
        <span>{data ? `${data.total} records` : ""}</span>
        <button type="button" disabled={page <= 1 || loading} onClick={() => setPage((value) => value - 1)}>Previous</button>
        <span>Page {page}</span>
        <button type="button" disabled={!data || page * data.page_size >= data.total || loading} onClick={() => setPage((value) => value + 1)}>Next</button>
      </div>
      {selected && (
        <section className="detail-panel" aria-labelledby="order-detail-title">
          <div className="detail-heading"><div><span className="kicker">ORDER DETAILS</span><h2 id="order-detail-title">{selected.reference}</h2></div>
            <button type="button" className="button-secondary" onClick={() => setSelected(null)}>Close</button></div>
          <div className="detail-grid">
            <div><span>Customer</span><strong>{selected.customer_name || "Guest"} · {selected.customer_phone}</strong></div>
            <div><span>Recipient</span><strong>{selected.recipient_phone}</strong></div>
            <div><span>Network / bundle</span><strong>{selected.network} · {selected.bundle}</strong></div>
            <div><span>Order status</span><strong>{selected.order_status.replaceAll("_", " ")}</strong></div>
            <div><span>Payment evidence</span><strong>{selected.payment_status}</strong></div>
            <div><span>Fulfilment evidence</span><strong>{selected.fulfillment_status}</strong></div>
            <div><span>Supplier</span><strong>{selected.supplier ?? "Not recorded"}</strong></div>
            <div><span>Supplier transaction</span><strong>{selected.supplier_reference ?? "Not recorded"}</strong></div>
            <div><span>Agent</span><strong>{selected.agent ?? "Not recorded"}</strong></div>
          </div>
          <h3>Status timeline</h3>
          <ol className="timeline">{selected.timeline.map((item, index) => <li key={`${item.event_type}-${index}`}><strong>{(item.new_status ?? item.event_type).replaceAll("_", " ")}</strong><span>{item.actor_label}{item.reason ? ` · ${item.reason}` : ""} · {new Date(item.created_at).toLocaleString()}</span></li>)}</ol>
          {selected.is_sample && <p className="notice">Sample order only. No payment or supplier delivery is connected.</p>}
          <h3>Support notes</h3>
          {selected.failure_reason && <p className="notice">Recorded failure reason: {selected.failure_reason}</p>}
          {!selected.failure_reason && selected.order_status === "failed" && <p className="muted">No failure reason is recorded for this order.</p>}
          {selected.notes.map((item) => <article className="note" key={item.id}><p>{item.note}</p><small>{item.author_email} · {new Date(item.created_at).toLocaleString()}</small></article>)}
          {staff?.permissions.includes("orders.notes") && <form className="inline-form" onSubmit={(event) => void submitNote(event)}>
            <label htmlFor="support-note">Add internal note</label><textarea id="support-note" maxLength={2000} required value={note} onChange={(event) => setNote(event.target.value)} />
            <button disabled={loading || !note.trim()} type="submit">Save note</button>
          </form>}
          <h3>Escalations</h3>
          {selected.escalations.map((item) => <article className="note" key={item.id}><p>{item.reason}</p><small>{item.status} · {item.created_by_email} · {new Date(item.created_at).toLocaleString()}</small></article>)}
          {staff?.permissions.includes("orders.manage") && <form className="inline-form" onSubmit={(event) => void submitEscalation(event)}>
            <label htmlFor="escalation-reason">Escalate order</label><textarea id="escalation-reason" maxLength={500} required value={escalation} onChange={(event) => setEscalation(event.target.value)} />
            <button disabled={loading || !escalation.trim()} type="submit">Create escalation</button>
          </form>}
        </section>
      )}
    </section>
  );
}
