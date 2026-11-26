from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Customer, Membership, Project, Task, UsageSnapshot
from app.core.redis_client import get_redis
from app.modules.entitlements.service import get_entitlements

METRIC_LIMIT_KEY = {
    "seats": "max_seats",
    "projects": "max_projects",
    "tasks": "max_tasks",
    "customers": "max_customers",
}


async def recount(db: AsyncSession, org_id: UUID, metric: str) -> int:
    if metric == "seats":
        value = await db.scalar(
            select(func.count()).select_from(Membership).where(Membership.organization_id == org_id)
        )
    elif metric == "projects":
        value = await db.scalar(
            select(func.count()).select_from(Project).where(Project.organization_id == org_id)
        )
    elif metric == "tasks":
        value = await db.scalar(
            select(func.count()).select_from(Task).where(Task.organization_id == org_id)
        )
    elif metric == "customers":
        value = await db.scalar(
            select(func.count()).select_from(Customer).where(Customer.organization_id == org_id)
        )
    else:
        value = 0
    value = int(value or 0)
    redis = get_redis()
    await redis.set(f"usage:{org_id}:{metric}", value, ex=600)
    snap = await db.scalar(
        select(UsageSnapshot).where(
            UsageSnapshot.organization_id == org_id, UsageSnapshot.metric == metric
        )
    )
    if snap:
        snap.value = value
    else:
        db.add(UsageSnapshot(organization_id=org_id, metric=metric, value=value))
    return value


async def get_usage(db: AsyncSession, org_id: UUID) -> dict[str, int]:
    usage = {}
    for metric in METRIC_LIMIT_KEY:
        redis = get_redis()
        cached = await redis.get(f"usage:{org_id}:{metric}")
        if cached is not None:
            usage[metric] = int(cached)
        else:
            usage[metric] = await recount(db, org_id, metric)
    return usage


async def check_and_increment(db: AsyncSession, org_id: UUID, metric: str) -> None:
    ents = await get_entitlements(db, org_id)
    limit_key = METRIC_LIMIT_KEY[metric]
    limit = ents.get(limit_key)
    if limit is None:
        return
    limit = int(limit)
    current = await recount(db, org_id, metric)
    if current >= limit:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "usage_limit",
                "metric": metric,
                "limit": limit,
                "usage": current,
                "plan": ents.get("_plan_slug"),
            },
        )
