import { useState, type FormEvent } from "react";
import { api } from "../api";
import { useAuth } from "../auth";

export function SettingsPage() {
  const { refreshOrgs } = useAuth();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [token, setToken] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function createOrg(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const org = await api.createOrg(name, slug);
      localStorage.setItem("org_id", org.id);
      await refreshOrgs();
      setMessage(`Created ${org.name}`);
      setName("");
      setSlug("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  async function accept(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const org = await api.acceptInvite(token);
      localStorage.setItem("org_id", org.id);
      await refreshOrgs();
      setMessage(`Joined ${org.name}`);
      setToken("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  return (
    <div>
      <h1>Settings</h1>
      {message && <p className="ok">{message}</p>}
      {error && <p className="error">{error}</p>}

      <section className="panel">
        <h2>Create organization</h2>
        <form className="stack-form" onSubmit={createOrg}>
          <label>
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label>
            Slug
            <input
              value={slug}
              onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
              pattern="[a-z0-9-]+"
              required
            />
          </label>
          <button className="cta" type="submit">
            Create workspace
          </button>
        </form>
      </section>

      <section className="panel">
        <h2>Accept invite</h2>
        <form className="stack-form" onSubmit={accept}>
          <label>
            Invite token
            <input value={token} onChange={(e) => setToken(e.target.value)} required />
          </label>
          <button className="cta" type="submit">
            Join organization
          </button>
        </form>
      </section>
    </div>
  );
}
