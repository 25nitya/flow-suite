
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import OrgContext, require_permission
from app.core.models import Organization, Plan, Subscription
from app.core.schemas import (
    CheckoutRequest,
    CheckoutResponse,
    PlanOut,
    PortalResponse,
    RazorpayVerifyRequest,
    StubUpgradeRequest,
    SubscriptionOut,
)
from app.modules.audit.service import write_audit
from app.modules.entitlements.service import (
    features_to_dict,
    get_entitlements,
    invalidate_entitlements,
)
from app.modules.rbac.permissions import BILLING_MANAGE, MEMBER_READ
from app.modules.usage.service import get_usage

router = APIRouter(prefix="/billing", tags=["billing"])
settings = get_settings()

RAZORPAY_BASE_URL = "https://api.razorpay.com/v1"

# Demo configuration: subscriptions run for 12 monthly billing cycles.
SUBSCRIPTION_TOTAL_COUNT = 12


def _razorpay_ready() -> bool:
    return (
        bool(settings.razorpay_key_id)
        and bool(settings.razorpay_key_secret)
        and not settings.billing_stub_mode
    )


async def _razorpay_request(
    method: str,
    path: str,
    *,
    payload: dict | None = None,
) -> dict:
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(
            status_code=503,
            detail="Razorpay API credentials are not configured",
        )

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.request(
                method,
                f"{RAZORPAY_BASE_URL}{path}",
                auth=(
                    settings.razorpay_key_id,
                    settings.razorpay_key_secret,
                ),
                json=payload,
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not connect to Razorpay",
        ) from exc

    if response.is_error:
        try:
            error_data = response.json()
            description = (
                error_data.get("error", {}).get("description")
                or "Razorpay API request failed"
            )
        except ValueError:
            description = "Razorpay API request failed"

        raise HTTPException(
            status_code=502,
            detail=description,
        )

    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail="Invalid response received from Razorpay",
        ) from exc


async def _get_subscription_data(
    db: AsyncSession,
    organization_id: UUID,
):
    ents = await get_entitlements(db, organization_id)
    usage = await get_usage(db, organization_id)

    sub = await db.scalar(
        select(Subscription).where(
            Subscription.organization_id == organization_id
        )
    )

    plan = (
        await db.get(Plan, sub.plan_id)
        if sub
        else await db.scalar(
            select(Plan).where(Plan.slug == "free")
        )
    )

    return SubscriptionOut(
        plan_slug=plan.slug if plan else "free",
        plan_name=plan.name if plan else "Free",
        status=sub.status if sub else "active",
        current_period_end=sub.current_period_end if sub else None,
        entitlements=ents,
        usage=usage,
    )


@router.get("/summary", response_model=SubscriptionOut)
async def billing_summary(
    ctx: OrgContext = Depends(require_permission(MEMBER_READ)),
    db: AsyncSession = Depends(get_db),
):
    return await _get_subscription_data(db, ctx.organization_id)


@router.get("/subscription", response_model=SubscriptionOut)
async def current_subscription(
    ctx: OrgContext = Depends(require_permission(BILLING_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    return await _get_subscription_data(db, ctx.organization_id)


@router.get("/plans", response_model=list[PlanOut])
async def list_plans(db: AsyncSession = Depends(get_db)):
    plans = (
        await db.scalars(
            select(Plan)
            .options(selectinload(Plan.features))
            .where(Plan.is_active.is_(True))
            .order_by(Plan.rank)
        )
    ).all()

    return [
        PlanOut(
            id=p.id,
            slug=p.slug,
            name=p.name,
            description=p.description,
            rank=p.rank,
            features=features_to_dict(p),
            amount_paise=p.amount_paise,
            currency=p.currency,
            billing_interval=p.billing_interval,
        )
        for p in plans
    ]


async def _ensure_razorpay_plan(
    db: AsyncSession,
    plan: Plan,
) -> str:
    if plan.razorpay_plan_id:
        return plan.razorpay_plan_id

    if plan.amount_paise < 100:
        raise HTTPException(
            status_code=400,
            detail="Razorpay subscriptions require a paid plan",
        )

    result = await _razorpay_request(
        "POST",
        "/plans",
        payload={
            "period": plan.billing_interval,
            "interval": 1,
            "item": {
                "name": plan.name,
                "amount": plan.amount_paise,
                "currency": plan.currency,
                "description": plan.description[:255],
            },
            "notes": {
                "flowsuite_plan_slug": plan.slug,
            },
        },
    )

    razorpay_plan_id = result.get("id")
    if not razorpay_plan_id:
        raise HTTPException(
            status_code=502,
            detail="Razorpay did not return a plan ID",
        )

    plan.razorpay_plan_id = razorpay_plan_id
    await db.commit()

    return razorpay_plan_id


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    ctx: OrgContext = Depends(require_permission(BILLING_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.scalar(
        select(Plan).where(
            Plan.slug == body.plan_slug,
            Plan.is_active.is_(True),
        )
    )

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    org = await db.get(Organization, ctx.organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if not _razorpay_ready():
        url = (
            f"{settings.frontend_url}/app/billing"
            f"?stub_upgrade={plan.slug}"
        )

        await write_audit(
            db,
            organization_id=ctx.organization_id,
            actor_id=ctx.user.id,
            action="billing.checkout_stub",
            entity_type="subscription",
            metadata={"plan": plan.slug},
        )
        await db.commit()

        return CheckoutResponse(url=url, stub=True)

    razorpay_plan_id = await _ensure_razorpay_plan(db, plan)

    result = await _razorpay_request(
        "POST",
        "/subscriptions",
        payload={
            "plan_id": razorpay_plan_id,
            "total_count": SUBSCRIPTION_TOTAL_COUNT,
            "quantity": 1,
            "customer_notify": 1,
            "notes": {
                "organization_id": str(ctx.organization_id),
                "plan_slug": plan.slug,
            },
        },
    )

    subscription_id = result.get("id")
    if not subscription_id:
        raise HTTPException(
            status_code=502,
            detail="Razorpay did not return a subscription ID",
        )

    await write_audit(
        db,
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        action="billing.checkout",
        entity_type="subscription",
        metadata={
            "plan": plan.slug,
            "razorpay_subscription_id": subscription_id,
        },
    )
    await db.commit()

    return CheckoutResponse(
        subscription_id=subscription_id,
        key_id=settings.razorpay_key_id,
        stub=False,
    )


@router.post("/verify", response_model=SubscriptionOut)
async def verify_checkout(
    body: RazorpayVerifyRequest,
    ctx: OrgContext = Depends(require_permission(BILLING_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    if not _razorpay_ready():
        raise HTTPException(
            status_code=400,
            detail="Razorpay verification is unavailable in stub mode",
        )

    # Razorpay subscription Checkout signature:
    # HMAC_SHA256(payment_id + "|" + subscription_id, key_secret)
    message = (
        f"{body.razorpay_payment_id}|"
        f"{body.razorpay_subscription_id}"
    )

    expected_signature = hmac.new(
        settings.razorpay_key_secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(
        expected_signature,
        body.razorpay_signature,
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid Razorpay payment signature",
        )

    subscription_data = await _razorpay_request(
        "GET",
        f"/subscriptions/{body.razorpay_subscription_id}",
    )

    notes = subscription_data.get("notes") or {}

    if notes.get("organization_id") != str(ctx.organization_id):
        raise HTTPException(
            status_code=403,
            detail="This subscription does not belong to your organization",
        )

    plan_slug = notes.get("plan_slug")
    if not plan_slug:
        raise HTTPException(
            status_code=400,
            detail="Subscription is missing its plan information",
        )

    plan = await db.scalar(
        select(Plan).where(Plan.slug == plan_slug)
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    razorpay_status = subscription_data.get("status")

    if razorpay_status not in {"active", "authenticated"}:
        raise HTTPException(
            status_code=409,
            detail=(
                "Razorpay has not activated this subscription yet. "
                "Please wait for confirmation and refresh billing."
            ),
        )

    current_end = subscription_data.get("current_end")
    period_end = (
        datetime.fromtimestamp(current_end, tz=timezone.utc)
        if current_end
        else None
    )

    await _apply_plan(
        db,
        ctx.organization_id,
        plan,
        status="active",
        razorpay_sub_id=body.razorpay_subscription_id,
        period_end=period_end,
    )

    await write_audit(
        db,
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        action="billing.razorpay_verified",
        entity_type="subscription",
        metadata={
            "plan": plan.slug,
            "razorpay_subscription_id": body.razorpay_subscription_id,
            "razorpay_payment_id": body.razorpay_payment_id,
        },
    )

    await db.commit()
    await invalidate_entitlements(ctx.organization_id)

    return await _get_subscription_data(db, ctx.organization_id)


@router.post("/portal", response_model=PortalResponse)
async def create_portal(
    ctx: OrgContext = Depends(require_permission(BILLING_MANAGE)),
):
    return PortalResponse(
        url=None,
        stub=False,
        message=(
            "Razorpay does not provide a hosted customer billing portal "
            "for this integration. Subscription management will be "
            "available through Flow Suite."
        ),
    )


@router.post("/stub-upgrade", response_model=SubscriptionOut)
async def stub_upgrade(
    body: StubUpgradeRequest,
    ctx: OrgContext = Depends(require_permission(BILLING_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    if _razorpay_ready():
        raise HTTPException(
            status_code=400,
            detail="Stub upgrade is disabled when Razorpay is configured",
        )

    plan = await db.scalar(
        select(Plan).where(Plan.slug == body.plan_slug)
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    await _apply_plan(
        db,
        ctx.organization_id,
        plan,
        status="active",
        razorpay_sub_id=None,
    )

    await write_audit(
        db,
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        action="billing.stub_upgrade",
        entity_type="subscription",
        metadata={"plan": plan.slug},
    )

    await db.commit()
    await invalidate_entitlements(ctx.organization_id)

    return await _get_subscription_data(db, ctx.organization_id)


async def _apply_plan(
    db: AsyncSession,
    org_id: UUID,
    plan: Plan,
    *,
    status: str,
    razorpay_sub_id: str | None,
    period_end: datetime | None = None,
):
    sub = await db.scalar(
        select(Subscription).where(
            Subscription.organization_id == org_id
        )
    )

    if sub:
        sub.plan_id = plan.id
        sub.status = status
        sub.razorpay_subscription_id = razorpay_sub_id
        sub.current_period_end = period_end
    else:
        db.add(
            Subscription(
                organization_id=org_id,
                plan_id=plan.id,
                status=status,
                razorpay_subscription_id=razorpay_sub_id,
                current_period_end=period_end,
            )
        )

    await invalidate_entitlements(org_id)


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not settings.razorpay_webhook_secret:
        raise HTTPException(
            status_code=503,
            detail="Razorpay webhook secret is not configured",
        )

    raw_body = await request.body()
    received_signature = request.headers.get(
        "X-Razorpay-Signature",
        "",
    )

    expected_signature = hmac.new(
        settings.razorpay_webhook_secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(
        expected_signature,
        received_signature,
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid Razorpay webhook signature",
        )

    try:
        event = json.loads(raw_body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid webhook JSON",
        ) from exc

    event_type = event.get("event", "")
    payload = event.get("payload") or {}
    subscription_entity = (
        (payload.get("subscription") or {}).get("entity") or {}
    )

    supported_events = {
        "subscription.activated",
        "subscription.charged",
        "subscription.resumed",
        "subscription.cancelled",
        "subscription.halted",
        "subscription.paused",
        "subscription.completed",
    }

    if event_type not in supported_events:
        return {"received": True, "ignored": True}

    notes = subscription_entity.get("notes") or {}
    org_id_value = notes.get("organization_id")
    plan_slug = notes.get("plan_slug")
    subscription_id = subscription_entity.get("id")

    if not org_id_value or not subscription_id:
        return {"received": True, "ignored": True}

    try:
        org_id = UUID(org_id_value)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid organization ID in subscription notes",
        )

    existing = await db.scalar(
        select(Subscription).where(
            Subscription.organization_id == org_id
        )
    )

    # Do not let an old subscription event overwrite a newer subscription.
    if (
        existing
        and existing.razorpay_subscription_id
        and existing.razorpay_subscription_id != subscription_id
    ):
        return {"received": True, "ignored": True}

    if event_type in {
        "subscription.activated",
        "subscription.charged",
        "subscription.resumed",
    }:
        if not plan_slug:
            return {"received": True, "ignored": True}

        plan = await db.scalar(
            select(Plan).where(Plan.slug == plan_slug)
        )
        if not plan:
            return {"received": True, "ignored": True}

        current_end = subscription_entity.get("current_end")
        period_end = (
            datetime.fromtimestamp(current_end, tz=timezone.utc)
            if current_end
            else None
        )

        await _apply_plan(
            db,
            org_id,
            plan,
            status="active",
            razorpay_sub_id=subscription_id,
            period_end=period_end,
        )

    else:
        free_plan = await db.scalar(
            select(Plan).where(Plan.slug == "free")
        )

        if free_plan:
            await _apply_plan(
                db,
                org_id,
                free_plan,
                status="active",
                razorpay_sub_id=None,
            )

    await write_audit(
        db,
        organization_id=org_id,
        actor_id=None,
        action="billing.razorpay_webhook",
        entity_type="subscription",
        metadata={
            "event": event_type,
            "razorpay_subscription_id": subscription_id,
        },
    )

    await db.commit()
    await invalidate_entitlements(org_id)

    return {"received": True}
