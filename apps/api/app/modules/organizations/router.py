from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import OrgContext, get_current_user, get_org_context, require_permission
from app.core.models import Invite, Membership, Organization, Plan, Subscription, User
from app.core.schemas import (
    InviteAccept,
    InviteCreate,
    InviteOut,
    MemberOut,
    OrgCreate,
    OrgOut,
)
from app.modules.audit.service import write_audit
from app.modules.rbac.permissions import MEMBER_INVITE, MEMBER_MANAGE, MEMBER_READ, Role
from app.modules.usage.service import check_and_increment, recount

router = APIRouter(prefix="/orgs", tags=["organizations"])


@router.post("", response_model=OrgOut)
async def create_org(
    body: OrgCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.scalar(select(Organization).where(Organization.slug == body.slug))
    if existing:
        raise HTTPException(status_code=400, detail="Slug already taken")
    org = Organization(name=body.name, slug=body.slug)
    db.add(org)
    await db.flush()
    db.add(Membership(organization_id=org.id, user_id=user.id, role=Role.owner.value))
    free = await db.scalar(select(Plan).where(Plan.slug == "free"))
    if free:
        db.add(Subscription(organization_id=org.id, plan_id=free.id, status="active"))
    await write_audit(
        db,
        organization_id=org.id,
        actor_id=user.id,
        action="org.create",
        entity_type="organization",
        entity_id=str(org.id),
        metadata={"name": org.name, "slug": org.slug},
    )
    await db.commit()
    await db.refresh(org)
    await recount(db, org.id, "seats")
    await db.commit()
    return OrgOut(id=org.id, name=org.name, slug=org.slug, role=Role.owner.value)


@router.get("", response_model=list[OrgOut])
async def list_orgs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Organization, Membership.role)
            .join(Membership, Membership.organization_id == Organization.id)
            .where(Membership.user_id == user.id)
            .order_by(Organization.name)
        )
    ).all()
    return [OrgOut(id=o.id, name=o.name, slug=o.slug, role=role) for o, role in rows]


@router.get("/current", response_model=OrgOut)
async def current_org(ctx: OrgContext = Depends(get_org_context), db: AsyncSession = Depends(get_db)):
    org = await db.get(Organization, ctx.organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    return OrgOut(id=org.id, name=org.name, slug=org.slug, role=ctx.role)


@router.get("/members", response_model=list[MemberOut])
async def list_members(
    ctx: OrgContext = Depends(require_permission(MEMBER_READ)),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(Membership, User)
            .join(User, User.id == Membership.user_id)
            .where(Membership.organization_id == ctx.organization_id)
        )
    ).all()
    return [
        MemberOut(user_id=u.id, email=u.email, full_name=u.full_name, role=m.role) for m, u in rows
    ]


@router.patch("/members/{user_id}")
async def update_member_role(
    user_id: UUID,
    role: str = Query(...),
    ctx: OrgContext = Depends(require_permission(MEMBER_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    if role not in {r.value for r in Role}:
        raise HTTPException(status_code=400, detail="Invalid role")
    if role == Role.owner.value and ctx.role != Role.owner.value:
        raise HTTPException(status_code=403, detail="Only owner can assign owner")
    m = await db.scalar(
        select(Membership).where(
            Membership.organization_id == ctx.organization_id, Membership.user_id == user_id
        )
    )
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    if m.role == Role.owner.value and role != Role.owner.value:
        owner_count = len(
            (
                await db.scalars(
                    select(Membership).where(
                        Membership.organization_id == ctx.organization_id,
                        Membership.role == Role.owner.value,
                    )
                )
            ).all()
        )
        if owner_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last owner")
    old = m.role
    m.role = role
    await write_audit(
        db,
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        action="member.role_change",
        entity_type="membership",
        entity_id=str(m.id),
        metadata={"user_id": str(user_id), "from": old, "to": role},
    )
    await db.commit()
    return {"ok": True}


@router.post("/invites", response_model=InviteOut)
async def create_invite(
    body: InviteCreate,
    ctx: OrgContext = Depends(require_permission(MEMBER_INVITE)),
    db: AsyncSession = Depends(get_db),
):
    await check_and_increment(db, ctx.organization_id, "seats")
    invite = Invite(
        organization_id=ctx.organization_id,
        email=body.email.lower(),
        role=body.role if body.role != Role.owner.value else Role.member.value,
        invited_by=ctx.user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invite)
    await write_audit(
        db,
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        action="invite.create",
        entity_type="invite",
        entity_id=str(invite.id),
        metadata={"email": invite.email, "role": invite.role},
    )
    await db.commit()
    await db.refresh(invite)
    return InviteOut.model_validate(invite)


@router.get("/invites", response_model=list[InviteOut])
async def list_invites(
    ctx: OrgContext = Depends(require_permission(MEMBER_INVITE)),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.scalars(
            select(Invite)
            .where(Invite.organization_id == ctx.organization_id, Invite.accepted_at.is_(None))
            .order_by(Invite.created_at.desc())
        )
    ).all()
    return [InviteOut.model_validate(r) for r in rows]


@router.post("/invites/accept", response_model=OrgOut)
async def accept_invite(
    body: InviteAccept,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    invite = await db.scalar(select(Invite).where(Invite.token == body.token))
    if not invite or invite.accepted_at:
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invite expired")
    if invite.email.lower() != user.email.lower():
        raise HTTPException(status_code=403, detail="Invite email mismatch")
    existing = await db.scalar(
        select(Membership).where(
            Membership.organization_id == invite.organization_id, Membership.user_id == user.id
        )
    )
    if not existing:
        await check_and_increment(db, invite.organization_id, "seats")
        db.add(
            Membership(
                organization_id=invite.organization_id, user_id=user.id, role=invite.role
            )
        )
    invite.accepted_at = datetime.now(timezone.utc)
    await write_audit(
        db,
        organization_id=invite.organization_id,
        actor_id=user.id,
        action="invite.accept",
        entity_type="invite",
        entity_id=str(invite.id),
    )
    await db.commit()
    org = await db.get(Organization, invite.organization_id)
    await recount(db, invite.organization_id, "seats")
    await db.commit()
    return OrgOut(id=org.id, name=org.name, slug=org.slug, role=invite.role)
