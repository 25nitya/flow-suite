from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.models import Membership, User
from app.core.security import decode_token
from app.modules.rbac.permissions import role_has_permission

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(creds.credentials)
        if payload.get("type") != "access":
            raise ValueError("bad type")
        user_id = UUID(payload["sub"])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


class OrgContext:
    def __init__(self, user: User, organization_id: UUID, role: str, membership: Membership):
        self.user = user
        self.organization_id = organization_id
        self.role = role
        self.membership = membership


async def get_org_context(
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrgContext:
    if not x_org_id:
        raise HTTPException(status_code=400, detail="X-Org-Id header required")
    try:
        org_id = UUID(x_org_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid X-Org-Id") from exc
    membership = await db.scalar(
        select(Membership).where(Membership.organization_id == org_id, Membership.user_id == user.id)
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    return OrgContext(user=user, organization_id=org_id, role=membership.role, membership=membership)


def require_permission(permission: str):
    async def _dep(ctx: OrgContext = Depends(get_org_context)) -> OrgContext:
        if not role_has_permission(ctx.role, permission):
            raise HTTPException(
                status_code=403,
                detail={"code": "forbidden", "permission": permission, "role": ctx.role},
            )
        return ctx

    return _dep
