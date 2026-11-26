import { NavLink, Outlet, Navigate } from "react-router-dom";
import { useAuth } from "../auth";

export function AppShell() {
  const { user, orgs, orgId, setOrgId, logout, loading } = useAuth();

  if (loading) return <div className="page center">Loading…</div>;
  if (!user) return <Navigate to="/" replace />;

  const role = orgs.find((o) => o.id === orgId)?.role;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="side-brand">Flow Suite</div>
        <label className="org-switch">
          Workspace
          <select value={orgId ?? ""} onChange={(e) => setOrgId(e.target.value)}>
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name} ({o.role})
              </option>
            ))}
          </select>
        </label>
        <nav>
          <NavLink to="/app" end>
            Home
          </NavLink>
          <NavLink to="/app/customers">Customers</NavLink>
          <NavLink to="/app/projects">Projects</NavLink>
          <NavLink to="/app/team">Team</NavLink>
          {role === "owner" && <NavLink to="/app/billing">Billing</NavLink>}
          {(role === "owner" || role === "admin") && <NavLink to="/app/audit">Audit</NavLink>}
          <NavLink to="/app/settings">Settings</NavLink>
        </nav>
        <div className="side-foot">
          <span>{user.full_name}</span>
          <button type="button" className="ghost" onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="main">
        {!orgId ? (
          <div className="panel">
            <h1>Create a workspace</h1>
            <p className="lede">You need an organization before managing customers and projects.</p>
            <NavLink className="cta inline" to="/app/settings">
              Go to settings
            </NavLink>
          </div>
        ) : (
          <Outlet />
        )}
      </main>
    </div>
  );
}
