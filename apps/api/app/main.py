
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.modules.auth.router import router as auth_router
from app.modules.organizations.router import router as orgs_router
from app.modules.customers.router import router as customers_router
from app.modules.projects.router import router as projects_router
from app.modules.billing.router import router as billing_router
from app.modules.audit.router import router as audit_router


settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prefix = settings.api_prefix
app.include_router(auth_router, prefix=prefix)
app.include_router(orgs_router, prefix=prefix)
app.include_router(customers_router, prefix=prefix)
app.include_router(projects_router, prefix=prefix)
app.include_router(billing_router, prefix=prefix)
app.include_router(audit_router, prefix=prefix)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "flow-suite-api"}
