# Flow Suite

Multi-tenant B2B SaaS: isolated organization workspaces, RBAC, customers/projects/tasks, Stripe test billing, feature entitlements, usage limits, and audit logging.

## Stack

- **API:** FastAPI (modular monolith) — port **8090**
- **Web:** React + TypeScript (Vite) — port **3001**
- **Postgres** 16 · **Redis** 7 · Docker Compose

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Open **http://localhost:3001**

| Account | Email | Password | Role |
|---------|-------|----------|------|
| Owner | `owner@flowsuite.com` | `owner123` | owner of Acme Demo |
| Member | `member@flowsuite.com` | `member123` | member |

### Stripe (optional)

Leave `BILLING_STUB_MODE=true` for local upgrades without Stripe. For real Checkout/Portal:

```env
BILLING_STUB_MODE=false
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_BUSINESS=price_...
```

Webhook endpoint: `POST http://localhost:8090/api/billing/webhook`

### Smoke test

```bash
chmod +x scripts/smoke.sh
./scripts/smoke.sh
```

## Docs

- **[FLOWS.md](FLOWS.md)** — tenancy, RBAC, CRM/work, billing, entitlements, usage, audit

## Layout

```
flow-suite/
  apps/api/     # FastAPI
  apps/web/     # React
  scripts/      # seed + smoke
```
