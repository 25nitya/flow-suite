from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.models import Plan, PlanFeature, Subscription
from app.core.redis_client import get_redis

DEFAULT_FREE_ENTITLEMENTS = {
    "max_seats": 3,
    "max_projects": 3,
    "max_tasks": 50,
    "max_customers": 25,
    "audit_log": False,
    "advanced_reports": False,
    "sso": False,
}


async def get_org_plan(db: AsyncSession, org_id: UUID) -> Plan:
    sub = await db.scalar(select(Subscription).where(Subscription.organization_id == org_id))
    if sub:
        plan = await db.scalar(
            select(Plan).options(selectinload(Plan.features)).where(Plan.id == sub.plan_id)
        )
        if plan:
            return plan
    plan = await db.scalar(
        select(Plan).options(selectinload(Plan.features)).where(Plan.slug == "free")
    )
    if not plan:
        raise RuntimeError("Free plan missing — run seed")
    return plan


def features_to_dict(plan: Plan) -> dict:
    out: dict = {}
    for f in plan.features:
        if f.limit_value is not None:
            out[f.feature_key] = f.limit_value
        else:
            out[f.feature_key] = f.enabled
    # ensure defaults
    for k, v in DEFAULT_FREE_ENTITLEMENTS.items():
        out.setdefault(k, v)
    return out


async def get_entitlements(db: AsyncSession, org_id: UUID) -> dict:
    redis = get_redis()
    key = f"entitlements:{org_id}"
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)
    plan = await get_org_plan(db, org_id)
    data = features_to_dict(plan)
    data["_plan_slug"] = plan.slug
    data["_plan_name"] = plan.name
    await redis.set(key, json.dumps(data), ex=300)
    return data


async def invalidate_entitlements(org_id: UUID) -> None:
    await get_redis().delete(f"entitlements:{org_id}")


async def require_feature(db: AsyncSession, org_id: UUID, feature_key: str) -> dict:
    from fastapi import HTTPException

    ents = await get_entitlements(db, org_id)
    val = ents.get(feature_key)
    if val is False or val is None:
        raise HTTPException(
            status_code=402,
            detail={"code": "feature_locked", "feature": feature_key, "plan": ents.get("_plan_slug")},
        )
    return ents
