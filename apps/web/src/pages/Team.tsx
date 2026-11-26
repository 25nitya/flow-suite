import { useEffect, useState, type FormEvent } from "react";
import { api, type Invite, type Member } from "../api";

export function TeamPage() {
  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [error, setError] = useState("");
  const [lastToken, setLastToken] = useState("");

  async function load() {
    setMembers(await api.members());
    try {
      setInvites(await api.invites());
    } catch {
      setInvites([]);
    }
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);

  async function invite(e: FormEvent) {
    e.preventDefault();
    try {
      const inv = await api.createInvite(email, role);
      setLastToken(inv.token);
      setEmail("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  return (
    <div>
      <h1>Team</h1>
      {error && <p className="error">{error}</p>}
      <table className="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
          </tr>
        </thead>
        <tbody>
          {members.map((m) => (
            <tr key={m.user_id}>
              <td>{m.full_name}</td>
              <td>{m.email}</td>
              <td>
                <select
                  value={m.role}
                  onChange={(e) =>
                    api
                      .updateMemberRole(m.user_id, e.target.value)
                      .then(load)
                      .catch((err) => setError(err.message))
                  }
                >
                  <option value="owner">owner</option>
                  <option value="admin">admin</option>
                  <option value="member">member</option>
                  <option value="viewer">viewer</option>
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Invite</h2>
      <form className="inline-form" onSubmit={invite}>
        <input type="email" placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="admin">admin</option>
          <option value="member">member</option>
          <option value="viewer">viewer</option>
        </select>
        <button className="cta" type="submit">
          Send invite
        </button>
      </form>
      {lastToken && (
        <p className="hint">
          Demo invite token (share with invitee after they register with matching email):{" "}
          <code>{lastToken}</code>
        </p>
      )}
      <ul className="list">
        {invites.map((i) => (
          <li key={i.id}>
            {i.email} · {i.role} · token <code>{i.token}</code>
          </li>
        ))}
      </ul>
    </div>
  );
}
