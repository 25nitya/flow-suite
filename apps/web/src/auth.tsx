import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, type Org, type User } from "./api";

type AuthState = {
  user: User | null;
  orgs: Org[];
  orgId: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
  setOrgId: (id: string) => void;
  refreshOrgs: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [orgId, setOrgIdState] = useState<string | null>(localStorage.getItem("org_id"));
  const [loading, setLoading] = useState(true);

  const refreshOrgs = useCallback(async () => {
    const list = await api.orgs();
    setOrgs(list);
    const current = localStorage.getItem("org_id");
    if (current && list.some((o) => o.id === current)) {
      setOrgIdState(current);
    } else if (list[0]) {
      localStorage.setItem("org_id", list[0].id);
      setOrgIdState(list[0].id);
    } else {
      localStorage.removeItem("org_id");
      setOrgIdState(null);
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then(async (u) => {
        setUser(u);
        await refreshOrgs();
      })
      .catch(() => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
      })
      .finally(() => setLoading(false));
  }, [refreshOrgs]);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await api.login(email, password);
      localStorage.setItem("access_token", res.access_token);
      localStorage.setItem("refresh_token", res.refresh_token);
      setUser(res.user);
      await refreshOrgs();
    },
    [refreshOrgs],
  );

  const register = useCallback(
    async (email: string, password: string, fullName: string) => {
      const res = await api.register(email, password, fullName);
      localStorage.setItem("access_token", res.access_token);
      localStorage.setItem("refresh_token", res.refresh_token);
      setUser(res.user);
      await refreshOrgs();
    },
    [refreshOrgs],
  );

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("org_id");
    setUser(null);
    setOrgs([]);
    setOrgIdState(null);
  }, []);

  const setOrgId = useCallback((id: string) => {
    localStorage.setItem("org_id", id);
    setOrgIdState(id);
  }, []);

  const value = useMemo(
    () => ({ user, orgs, orgId, loading, login, register, logout, setOrgId, refreshOrgs }),
    [user, orgs, orgId, loading, login, register, logout, setOrgId, refreshOrgs],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside provider");
  return ctx;
}
