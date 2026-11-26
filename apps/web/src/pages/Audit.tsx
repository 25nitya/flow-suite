import { useEffect, useState } from "react";
import { api, type AuditRow } from "../api";

export function AuditPage() {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .audit()
      .then(setRows)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <h1>Audit log</h1>
      <p className="lede">Owner/admin only. Requires Pro+ <code>audit_log</code> entitlement.</p>
      {error && <p className="error">{error}</p>}
      <table className="table">
        <thead>
          <tr>
            <th>When</th>
            <th>Action</th>
            <th>Entity</th>
            <th>Meta</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>{new Date(r.created_at).toLocaleString()}</td>
              <td>{r.action}</td>
              <td>
                {r.entity_type} {r.entity_id}
              </td>
              <td>
                <code>{JSON.stringify(r.metadata)}</code>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
