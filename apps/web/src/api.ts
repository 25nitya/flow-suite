
export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8090";

export type User = { id: string; email: string; full_name: string };
export type Org = { id: string; name: string; slug: string; role?: string | null };

export type Customer = {
  id: string;
  name: string;
  email: string | null;
  company: string | null;
  notes: string;
  created_at: string;
};

export type Project = {
  id: string;
  name: string;
  description: string;
  status: string;
  customer_id: string | null;
  created_at: string;
};

export type Task = {
  id: string;
  project_id: string;
  title: string;
  description: string;
  status: string;
  assignee_id: string | null;
  due_date: string | null;
  created_at: string;
};

export type Member = {
  user_id: string;
  email: string;
  full_name: string;
  role: string;
};

export type Invite = {
  id: string;
  email: string;
  role: string;
  token: string;
  expires_at: string;
  accepted_at: string | null;
};

export type Plan = {
  id: string;
  slug: string;
  name: string;
  description: string;
  rank: number;
  features: Record<string, unknown>;
  amount_paise: number;
  currency: string;
  billing_interval: string;
};

export type Subscription = {
  plan_slug: string;
  plan_name: string;
  status: string;
  current_period_end: string | null;
  entitlements: Record<string, unknown>;
  usage: Record<string, number>;
};

export type CheckoutResponse = {
  subscription_id: string | null;
  key_id: string | null;
  url: string | null;
  stub: boolean;
};

export type RazorpayVerification = {
  razorpay_payment_id: string;
  razorpay_subscription_id: string;
  razorpay_signature: string;
};

export type PortalResponse = {
  url: string | null;
  stub: boolean;
  message: string | null;
};

export type AuditRow = {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  actor_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

function headers(orgId?: string | null): HeadersInit {
  const h: Record<string, string> = {
    "Content-Type": "application/json",
  };

  const token = localStorage.getItem("access_token");

  if (token) {
    h.Authorization = `Bearer ${token}`;
  }

  const org = orgId ?? localStorage.getItem("org_id");

  if (org) {
    h["X-Org-Id"] = org;
  }

  return h;
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  orgId?: string | null,
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...headers(orgId),
      ...(init.headers || {}),
    },
  });

  if (!res.ok) {
    let detail: unknown = res.statusText;

    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      // Ignore non-JSON error responses.
    }

    const err = new Error(
      typeof detail === "string" ? detail : JSON.stringify(detail),
    );

    (err as Error & { detail: unknown }).detail = detail;

    throw err;
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}

export const api = {
  register: (email: string, password: string, full_name: string) =>
    request<{
      access_token: string;
      refresh_token: string;
      user: User;
    }>(
      "/api/auth/register",
      {
        method: "POST",
        body: JSON.stringify({ email, password, full_name }),
      },
      null,
    ),

  login: (email: string, password: string) =>
    request<{
      access_token: string;
      refresh_token: string;
      user: User;
    }>(
      "/api/auth/login",
      {
        method: "POST",
        body: JSON.stringify({ email, password }),
      },
      null,
    ),

  me: () => request<User>("/api/auth/me", {}, null),

  orgs: () => request<Org[]>("/api/orgs", {}, null),

  createOrg: (name: string, slug: string) =>
    request<Org>(
      "/api/orgs",
      {
        method: "POST",
        body: JSON.stringify({ name, slug }),
      },
      null,
    ),

  acceptInvite: (token: string) =>
    request<Org>(
      "/api/orgs/invites/accept",
      {
        method: "POST",
        body: JSON.stringify({ token }),
      },
      null,
    ),

  members: () => request<Member[]>("/api/orgs/members"),

  invites: () => request<Invite[]>("/api/orgs/invites"),

  createInvite: (email: string, role: string) =>
    request<Invite>("/api/orgs/invites", {
      method: "POST",
      body: JSON.stringify({ email, role }),
    }),

  updateMemberRole: (userId: string, role: string) =>
    request(
      `/api/orgs/members/${userId}?role=${encodeURIComponent(role)}`,
      { method: "PATCH" },
    ),

  customers: () => request<Customer[]>("/api/customers"),

  createCustomer: (body: Partial<Customer> & { name: string }) =>
    request<Customer>("/api/customers", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  deleteCustomer: (id: string) =>
    request(`/api/customers/${id}`, { method: "DELETE" }),

  projects: () => request<Project[]>("/api/projects"),

  createProject: (
    body: {
      name: string;
      description?: string;
      customer_id?: string | null;
    },
  ) =>
    request<Project>("/api/projects", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  deleteProject: (id: string) =>
    request(`/api/projects/${id}`, { method: "DELETE" }),

  tasks: (projectId: string) =>
    request<Task[]>(`/api/projects/${projectId}/tasks`),

  createTask: (
    projectId: string,
    body: { title: string; status?: string },
  ) =>
    request<Task>(`/api/projects/${projectId}/tasks`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateTask: (taskId: string, body: Partial<Task>) =>
    request<Task>(`/api/tasks/${taskId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  deleteTask: (taskId: string) =>
    request(`/api/tasks/${taskId}`, { method: "DELETE" }),

  // Billing APIs

  plans: () =>
    request<Plan[]>("/api/billing/plans", {}, null),

  billingSummary: () =>
    request<Subscription>("/api/billing/summary"),

  checkout: (plan_slug: string) =>
    request<CheckoutResponse>("/api/billing/checkout", {
      method: "POST",
      body: JSON.stringify({ plan_slug }),
    }),

  verifyCheckout: (body: RazorpayVerification) =>
    request<Subscription>("/api/billing/verify", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  portal: () =>
    request<PortalResponse>("/api/billing/portal", {
      method: "POST",
    }),

  stubUpgrade: (plan_slug: string) =>
    request<Subscription>("/api/billing/stub-upgrade", {
      method: "POST",
      body: JSON.stringify({ plan_slug }),
    }),

  audit: () => request<AuditRow[]>("/api/audit"),
};
