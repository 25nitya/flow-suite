import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Subscription } from "../api";
import { useAuth } from "../auth";

export function HomePage() {
  const { orgs, orgId } = useAuth();
  const [summary, setSummary] = useState<Subscription | null>(null);
  const org = orgs.find((o) => o.id === orgId);

  useEffect(() => {
    if (!orgId) return;
    api.billingSummary().then(setSummary).catch(() => setSummary(null));
  }, [orgId]);

  return (
    <div>
      <h1>{org?.name ?? "Workspace"}</h1>
      <p className="lede">Plan, customers, and delivery in one isolated tenant.</p>
      {summary && (
        <div className="meter-grid">
          <div className="meter">
            <span>Plan</span>
            <strong>{summary.plan_name}</strong>
          </div>
          {(["projects", "tasks", "customers", "seats"] as const).map((m) => {
            const limitKey = `max_${m}` as const;
            const limit = Number(summary.entitlements[limitKey] ?? 0);
            const used = summary.usage[m] ?? 0;
            return (
              <div className="meter" key={m}>
                <span>{m}</span>
                <strong>
                  {used} / {limit}
                </strong>
                <div className="bar">
                  <i style={{ width: `${Math.min(100, (used / Math.max(limit, 1)) * 100)}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
      <div className="quick-links">
        <Link to="/app/customers">Customers</Link>
        <Link to="/app/projects">Projects</Link>
        <Link to="/app/team">Invite teammates</Link>
      </div>
    </div>
  );
}
