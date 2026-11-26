import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export function LandingPage() {
  const { user, loading, login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("owner@flowsuite.com");
  const [password, setPassword] = useState("owner123");
  const [fullName, setFullName] = useState("Flow Owner");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (!loading && user) return <Navigate to="/app" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password, fullName);
      navigate("/app");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page landing">
      <div className="landing-bg" aria-hidden />
      <header className="landing-hero">
        <p className="brand">Flow Suite</p>
        <h1>Workspaces that scale with your subscription.</h1>
        <p className="lede">
          Isolated orgs, RBAC, customers, projects, and tasks — with Stripe billing, entitlements, and
          audit trails.
        </p>
        <form className="auth-card" onSubmit={onSubmit}>
          <div className="tabs">
            <button type="button" className={mode === "login" ? "on" : ""} onClick={() => setMode("login")}>
              Sign in
            </button>
            <button
              type="button"
              className={mode === "register" ? "on" : ""}
              onClick={() => setMode("register")}
            >
              Create account
            </button>
          </div>
          {mode === "register" && (
            <label>
              Full name
              <input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
            </label>
          )}
          <label>
            Work email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          {error && <p className="error">{error}</p>}
          <button className="cta" disabled={busy} type="submit">
            {busy ? "…" : mode === "login" ? "Enter workspace" : "Start free"}
          </button>
          <p className="hint">
            Demo owner: <code>owner@flowsuite.com</code> / <code>owner123</code>
          </p>
        </form>
      </header>
      <p className="landing-foot">
        <Link to="/app">Open app</Link>
      </p>
    </div>
  );
}
