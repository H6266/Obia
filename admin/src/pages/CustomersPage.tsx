import { useEffect, useState, type FormEvent } from "react";
import { api } from "../services/api";
import { useAuth } from "../auth/AuthContext";
import type { Customer, CustomerDetail, Page } from "../types";

export function CustomersPage() {
  const { staff } = useAuth();
  const [search, setSearch] = useState("");
  const [data, setData] = useState<Page<Customer> | null>(null);
  const [detail, setDetail] = useState<CustomerDetail | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);

  async function load(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ page: String(page), page_size: "25" });
      if (search.trim()) params.set("search", search.trim());
      setData(await api.customers(params));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not load customers.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [page]);

  async function toggleStatus(customer: Customer) {
    const next = customer.account_status === "suspended" ? "active" : "suspended";
    const reason = window.prompt(`Reason for ${next === "suspended" ? "suspension" : "reactivation"} (required):`);
    if (!reason?.trim()) return;
    setLoading(true);
    setError("");
    try {
      await api.setCustomerStatus(customer.id, next, reason.trim());
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not update customer status.");
      setLoading(false);
    }
  }

  async function viewCustomer(id: string) {
    setError("");
    setDetail(null);
    try {
      setDetail(await api.customer(id));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not load customer details.");
    }
  }

  return (
    <section>
      <header className="page-heading"><div><span className="kicker">CUSTOMER OPERATIONS</span><h1>Customers</h1>
        <p>Personal information is masked by default. Access, status changes, and reasons are recorded for audit.</p></div></header>
      <form className="toolbar" onSubmit={(event) => { setPage(1); void load(event); }}>
        <label>Search by name or account ID<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Name or UUID" /></label>
        <button type="submit" disabled={loading}>{loading ? "Searching…" : "Search"}</button>
      </form>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="table-scroll"><table>
        <thead><tr><th>Customer</th><th>Phone</th><th>Verified</th><th>Account status</th><th>Orders</th><th>Created</th><th>Action</th></tr></thead>
        <tbody>
          {data?.items.map((customer) => (
            <tr key={customer.id}>
              <td><strong>{customer.full_name || "Name not provided"}</strong><small>{customer.id}</small></td>
              <td>{customer.phone}</td><td>{customer.phone_verified ? "Verified" : "Unverified"}</td>
              <td>{customer.account_status}</td><td>{customer.order_count}</td><td>{new Date(customer.created_at).toLocaleDateString()}</td>
              <td><button className="button-secondary" type="button" onClick={() => void viewCustomer(customer.id)}>View</button>
                {staff?.permissions.includes("customers.manage") && <button className="button-secondary" disabled={loading} type="button" onClick={() => void toggleStatus(customer)}>{customer.account_status === "suspended" ? "Reactivate" : "Suspend"}</button>}</td>
            </tr>
          ))}
          {!data?.items.length && <tr><td className="empty-cell" colSpan={7}>{loading ? "Loading customers…" : "No customer accounts found."}</td></tr>}
        </tbody>
      </table></div>
      <div className="pagination"><span>{data ? `${data.total} records` : ""}</span>
        <button type="button" disabled={page <= 1 || loading} onClick={() => setPage((value) => value - 1)}>Previous</button><span>Page {page}</span>
        <button type="button" disabled={!data || page * data.page_size >= data.total || loading} onClick={() => setPage((value) => value + 1)}>Next</button>
      </div>
      {detail && <section className="detail-panel" aria-labelledby="customer-detail-title">
        <div className="detail-heading"><div><span className="kicker">CUSTOMER PROFILE</span><h2 id="customer-detail-title">{detail.full_name || "Name not provided"}</h2></div>
          <button type="button" className="button-secondary" onClick={() => setDetail(null)}>Close</button></div>
        <div className="detail-grid">
          <div><span>Phone</span><strong>{detail.phone}</strong></div>
          <div><span>Account status</span><strong>{detail.account_status}</strong></div>
          <div><span>Phone verification</span><strong>{detail.phone_verified ? "Verified" : "Unverified"}</strong></div>
          <div><span>Created</span><strong>{new Date(detail.created_at).toLocaleString()}</strong></div>
          <div><span>Account ID</span><strong>{detail.id}</strong></div>
          <div><span>Account orders</span><strong>{detail.order_count}</strong></div>
        </div>
        <h3>Order history</h3>
        {detail.orders.length ? <div className="table-scroll"><table>
          <thead><tr><th>Reference</th><th>Network · bundle</th><th>Amount</th><th>Order status</th><th>Payment</th><th>Fulfilment</th><th>Created</th></tr></thead>
          <tbody>{detail.orders.map((order) => <tr key={order.reference}><td>{order.reference}</td><td>{order.network} · {order.bundle}</td>
            <td>{order.currency} {Number(order.amount).toFixed(2)}</td><td>{order.order_status.replaceAll("_", " ")}</td>
            <td>{order.payment_status}</td><td>{order.fulfillment_status}</td><td>{new Date(order.created_at).toLocaleString()}</td></tr>)}</tbody>
        </table></div> : <p className="muted">No account-linked orders.</p>}
        <h3>Support records</h3>
        {detail.support_records.map((record) => <article className="note" key={record.id}>
          <p>{record.note}</p><small>Order {record.order_reference} · {record.author_email} · {new Date(record.created_at).toLocaleString()}</small>
        </article>)}
        {!detail.support_records.length && <p className="muted">No support notes recorded.</p>}
      </section>}
    </section>
  );
}
