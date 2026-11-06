import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { AuditRecord } from "../types";

export function AuditPage() {
  const [records, setRecords] = useState<AuditRecord[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api.audit(1).then(setRecords).catch((requestError: unknown) => {
      setError(requestError instanceof Error ? requestError.message : "Could not load audit records.");
    });
  }, []);

  return (
    <section>
      <header className="page-heading"><div><span className="kicker">GOVERNANCE</span><h1>Administrative audit log</h1>
        <p>Append-only record of staff access and administrative changes. Audit records cannot be changed through the API.</p></div></header>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="table-scroll"><table>
        <thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Resource</th><th>Reason / change</th><th>Request ID</th></tr></thead>
        <tbody>{records.map((item) => (
          <tr key={item.id}><td>{new Date(item.created_at).toLocaleString()}</td><td>{item.actor_email}</td>
            <td>{item.action}</td><td>{item.resource_type} · {item.resource_id}</td>
            <td>{item.reason ?? JSON.stringify(item.new_value ?? {})}</td><td>{item.request_id}</td></tr>
        ))}
          {!records.length && <tr><td className="empty-cell" colSpan={6}>{error ? "Audit log unavailable." : "No administrative events recorded yet."}</td></tr>}
        </tbody>
      </table></div>
    </section>
  );
}
