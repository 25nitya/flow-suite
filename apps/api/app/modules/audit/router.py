from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import OrgContext, require_permission
from app.core.models import AuditLog
from app.core.schemas import AuditOut
from app.modules.entitlements.service import require_feature
from app.modules.rbac.permissions import AUDIT_READ

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditOut])
async def list_audit(
    ctx: OrgContext = Depends(require_permission(AUDIT_READ)),
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
):
    await require_feature(db, ctx.organization_id, "audit_log")
    rows = (
        await db.scalars(
            select(AuditLog)
            .where(AuditLog.organization_id == ctx.organization_id)
            .order_by(AuditLog.created_at.desc())
            .limit(min(limit, 200))
        )
    ).all()
    return [AuditOut.model_validate(r) for r in rows]
