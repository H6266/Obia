import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { api } from "../services/api";
import type { DashboardMetrics } from "../types";

const periods = [
  ["today", "Today"],
  ["yesterday", "Yesterday"],
  ["last_7_days", "Last 7 days"],
  ["last_30_days", "Last 30 days"],
  ["this_month", "This month"],
  ["last_month", "Last month"],
  ["custom", "Custom range"],
] as const;

const money = (value: string | null) =>
  value === null ? "—" : `GHS ${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;

export function DashboardPage() {
  const { staff } = useAuth();
  const [period, setPeriod] = useState<string>("last_30_days");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [data, setData] = useState<DashboardMetrics | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    if (period === "custom" && (!startDate || !endDate)) {
      setLoading(false);
      return () => { active = false; };
    }
    api.dashboard(period, startDate, endDate)
      .then((result) => { if (active) setData(result); })
      .catch((requestError: unknown) => {
        if (active) setError(requestError instanceof Error ? requestError.message : "Could not load operations metrics.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [period, startDate, endDate]);

  if (loading && !data) return <p role="status">Loading verified operations data…</p>;
  if (error && !data) return <p className="error" role="alert">{error}</p>;
  if (!data) return null;

  const metrics = [
    { label: "Orders", value: data.total_orders.toLocaleString(), link: "/orders", permission: "orders.read" },
    { label: "Completed orders", value: data.successful_orders.toLocaleString(), link: "/orders?status=completed", permission: "orders.read" },
    { label: "Pending orders", value: data.pending_orders.toLocaleString(), link: "/orders?status=pending_payment", permission: "orders.read" },
    { label: "Failed orders", value: data.failed_orders.toLocaleString(), link: "/orders?status=failed", permission: "orders.read" },
    { label: "Sample-catalogue orders", value: data.sample_orders.toLocaleString(), link: "/orders", permission: "orders.read", note: "Excluded from business performance metrics." },
    { label: "Active customers", value: data.active_customers.toLocaleString(), link: "/customers", permission: "customers.read" },
    { label: "Requested order value", value: money(data.requested_order_value), link: "/orders", permission: "orders.read" },
    { label: "Verified revenue", value: money(data.revenue), link: "/orders", permission: "finance.read", note: data.data_availability.revenue },
    { label: "Gross profit", value: money(data.gross_profit), link: "/orders", permission: "finance.read", note: data.data_availability.profit },
  ];

  return (
    <section>
      <header className="page-heading">
        <div><span className="kicker">OWNER & ADMIN OPERATIONS</span><h1>Business overview</h1>
          <p>Database-backed order and customer activity. Unverified financial and inventory values remain unavailable.</p></div>
        <label className="period-filter">Date range
          <select value={period} onChange={(event) => {
            const value = event.target.value;
            if (value === "custom" && data) {
              setStartDate(data.start.slice(0, 10));
              setEndDate(new Date(new Date(data.end).getTime() - 86400000).toISOString().slice(0, 10));
            }
            setPeriod(value);
          }}>
            {periods.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
      </header>
      {period === "custom" && <div className="custom-dates">
        <label>From<input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} /></label>
        <label>To<input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} /></label>
      </div>}
      {period === "custom" && data && startDate > endDate && <p className="error" role="alert">Start date must be on or before end date.</p>}
      {error && <p className="error" role="alert">{error}</p>}
      <p className="data-period">Showing {new Date(data.start).toLocaleDateString()} – {new Date(new Date(data.end).getTime() - 1).toLocaleDateString()}</p>
      <div className="metric-grid">
        {metrics.map((metric) => (
          staff?.permissions.includes(metric.permission)
            ? <Link className="metric-card" key={metric.label} to={metric.link}>
                <span>{metric.label}</span><strong>{metric.value}</strong>
                {metric.note && <small>{metric.note}</small>}
              </Link>
            : <div className="metric-card" key={metric.label}>
                <span>{metric.label}</span><strong>{metric.value}</strong>
                {metric.note && <small>{metric.note}</small>}
              </div>
        ))}
      </div>
      {data.total_orders === 0 && (
        <div className="empty-panel">
          <h2>No orders in this period</h2>
          <p>Metrics will populate from persisted operations. No sample revenue, inventory or supplier values are being displayed.</p>
          <Link to="/orders">Open order centre</Link>
        </div>
      )}
      <div className="analytics-grid">
        <section className="panel"><h2>Orders over time</h2>
          {data.daily_orders.length ? data.daily_orders.map((item) => (
            <div className="bar-row" key={item.date} title={`${item.orders} orders; requested value ${money(String(item.requested_value))}`}>
              <span>{new Date(`${item.date}T00:00:00`).toLocaleDateString()}</span>
              <i style={{ width: `${Math.max(4, item.orders / Math.max(...data.daily_orders.map((row) => row.orders)) * 100)}%` }} />
              <b>{item.orders}</b>
            </div>
          )) : <p className="muted">No order activity recorded.</p>}
        </section>
        <section className="panel"><h2>Orders by network</h2>
          {data.orders_by_network.length ? data.orders_by_network.map((item) => (
            <div className="split-row" key={item.network}><span>{item.network}</span><strong>{item.orders}</strong></div>
          )) : <p className="muted">No order activity recorded.</p>}
          <h2 className="subheading">Status distribution</h2>
          {data.orders_by_status.length ? data.orders_by_status.map((item) => (
            <div className="split-row" key={item.status}><span>{item.status.replaceAll("_", " ")}</span><strong>{item.orders}</strong></div>
          )) : <p className="muted">No order activity recorded.</p>}
        </section>
      </div>
    </section>
  );
}
