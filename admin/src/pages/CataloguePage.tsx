import { useEffect, useState, type FormEvent } from "react";
import { api } from "../services/api";
import type {
  CatalogueBundle,
  CatalogueNetwork,
  CatalogueRevision,
  Page,
} from "../types";

export function CataloguePage() {
  const [networks, setNetworks] = useState<CatalogueNetwork[]>([]);
  const [networkId, setNetworkId] = useState("");
  const [search, setSearch] = useState("");
  const [bundles, setBundles] = useState<Page<CatalogueBundle> | null>(null);
  const [selected, setSelected] = useState<CatalogueBundle | null>(null);
  const [history, setHistory] = useState<CatalogueRevision[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [reason, setReason] = useState("");
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [size, setSize] = useState("");
  const [category, setCategory] = useState("");
  const [validity, setValidity] = useState("");
  const [available, setAvailable] = useState(false);

  useEffect(() => {
    api.catalogueNetworks()
      .then(setNetworks)
      .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Could not load networks."));
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    const params = new URLSearchParams({ page: String(page), page_size: "25" });
    if (networkId) params.set("network_id", networkId);
    if (search.trim()) params.set("search", search.trim());
    api.catalogueBundles(params)
      .then((result) => {
        if (active) {
          setBundles(result);
          if (selected) {
            setSelected(result.items.find((bundle) => bundle.id === selected.id) ?? null);
          }
        }
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : "Could not load catalogue.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [networkId, page, search]);

  useEffect(() => {
    if (!selected) {
      setHistory([]);
      return;
    }
    let active = true;
    setName(selected.name);
    setAmount(selected.amount);
    setSize(selected.size_gb);
    setCategory(selected.category);
    setValidity(selected.validity_days === null ? "" : String(selected.validity_days));
    setAvailable(selected.is_available);
    setReason("");
    api.bundleHistory(selected.id)
      .then((rows) => { if (active) setHistory(rows); })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : "Could not load catalogue history.");
      });
    return () => { active = false; };
  }, [selected?.id, selected?.updated_at]);

  async function saveBundle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected || saving) return;
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const updated = await api.updateBundle(selected.id, {
        name,
        amount,
        size_gb: size,
        category,
        validity_days: validity.trim() ? Number(validity) : null,
        is_available: available,
        reason: reason.trim(),
      });
      setSelected(updated);
      setNotice("Catalogue changes saved and recorded in the revision history.");
      const params = new URLSearchParams({ page: String(page), page_size: "25" });
      if (networkId) params.set("network_id", networkId);
      if (search.trim()) params.set("search", search.trim());
      setBundles(await api.catalogueBundles(params));
      setHistory(await api.bundleHistory(updated.id));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not save catalogue changes.");
    } finally {
      setSaving(false);
    }
  }

  async function toggleNetwork(network: CatalogueNetwork) {
    if (saving || !reason.trim()) return;
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const updated = await api.updateNetworkStatus(network.id, !network.is_active, reason.trim());
      setNetworks((current) => current.map((item) => item.id === network.id ? updated : item));
      setReason("");
      setNotice(`${updated.name} is now ${updated.is_active ? "active" : "inactive"}.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not update network status.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section>
      <header className="page-heading">
        <div><span className="kicker">CATALOGUE CONTROL</span><h1>Networks & bundles</h1>
          <p>Changes are permission-checked and recorded; existing orders retain their price snapshot.</p></div>
      </header>
      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="notice" role="status">{notice}</p>}
      <section className="panel">
        <h2>Network availability</h2>
        <div className="network-status-list">
          {networks.map((network) => (
            <div className="split-row" key={network.id}>
              <span>{network.name} · {network.is_active ? "Active" : "Inactive"}</span>
              <button
                type="button"
                className="button-secondary"
                disabled={saving || !reason.trim()}
                onClick={() => void toggleNetwork(network)}
              >
                {network.is_active ? "Deactivate" : "Activate"}
              </button>
            </div>
          ))}
          <label>Reason for network status change
            <input maxLength={500} value={reason} onChange={(event) => setReason(event.target.value)} />
          </label>
        </div>
      </section>
      <div className="catalogue-toolbar">
        <label>Network
          <select value={networkId} onChange={(event) => { setNetworkId(event.target.value); setPage(1); }}>
            <option value="">All networks</option>
            {networks.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </label>
        <label>Search bundles
          <input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} />
        </label>
      </div>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Bundle</th><th>Network</th><th>Size</th><th>Price</th><th>Availability</th><th /></tr></thead>
          <tbody>
            {bundles?.items.map((bundle) => (
              <tr key={bundle.id}>
                <td>{bundle.name}{bundle.is_sample ? " (sample)" : ""}</td>
                <td>{bundle.network_id}</td>
                <td>{bundle.size_gb} GB</td>
                <td>{bundle.currency} {bundle.amount}</td>
                <td>{bundle.is_available ? "Available" : "Unavailable"}</td>
                <td><button className="button-secondary" type="button" onClick={() => setSelected(bundle)}>Edit</button></td>
              </tr>
            ))}
            {!bundles?.items.length && <tr><td colSpan={6} className="empty-cell">{loading ? "Loading catalogue…" : "No bundles found."}</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="pagination">
        <span>{bundles ? `${bundles.total} records · page ${page}` : ""}</span>
        <button type="button" disabled={page <= 1 || loading} onClick={() => setPage((value) => value - 1)}>Previous</button>
        <button type="button" disabled={!bundles || page * bundles.page_size >= bundles.total || loading} onClick={() => setPage((value) => value + 1)}>Next</button>
      </div>
      {selected && (
        <section className="detail-panel">
          <div className="detail-heading"><div><span className="kicker">BUNDLE EDITOR</span><h2>{selected.name}</h2></div>
            <button type="button" className="button-secondary" onClick={() => setSelected(null)}>Close</button></div>
          <form className="catalogue-form" onSubmit={(event) => void saveBundle(event)}>
            <label>Name<input required maxLength={100} value={name} onChange={(event) => setName(event.target.value)} /></label>
            <label>Size (GB)<input required type="number" min="0.01" step="0.01" value={size} onChange={(event) => setSize(event.target.value)} /></label>
            <label>Price ({selected.currency})<input required type="number" min="0.01" step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} /></label>
            <label>Category<input required maxLength={32} value={category} onChange={(event) => setCategory(event.target.value)} /></label>
            <label>Validity (days; blank if unknown)<input type="number" min="1" step="1" value={validity} onChange={(event) => setValidity(event.target.value)} /></label>
            <label className="checkbox-field"><input type="checkbox" checked={available} onChange={(event) => setAvailable(event.target.checked)} /> Available to customers</label>
            <label className="full-width">Change reason<textarea required minLength={3} maxLength={500} value={reason} onChange={(event) => setReason(event.target.value)} /></label>
            <button type="submit" disabled={saving}>{saving ? "Saving…" : "Save catalogue changes"}</button>
          </form>
          <h3>Revision history</h3>
          {history.length ? history.map((revision) => (
            <article className="note" key={revision.id}>
              <p>{revision.reason}</p>
              <small>{revision.actor_email} · {new Date(revision.created_at).toLocaleString()}</small>
              <pre>{JSON.stringify(revision.new_value, null, 2)}</pre>
            </article>
          )) : <p className="muted">No catalogue changes recorded.</p>}
        </section>
      )}
    </section>
  );
}
