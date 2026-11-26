
"""Seed plans, demo user, and demo organization."""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.models import (
    Membership,
    Organization,
    Plan,
    PlanFeature,
    Subscription,
    User,
)
from app.core.security import hash_password
from app.modules.rbac.permissions import Role


PLAN_DEFS = [
    {
        "slug": "free",
        "name": "Free",
        "description": "For small teams exploring Flow Suite.",
        "rank": 0,
        "amount_paise": 0,
        "currency": "INR",
        "billing_interval": "monthly",
        "features": {
            "max_seats": 3,
            "max_projects": 3,
            "max_tasks": 50,
            "max_customers": 25,
            "audit_log": False,
            "advanced_reports": False,
            "sso": False,
        },
    },
    {
        "slug": "pro",
        "name": "Pro",
        "description": "Growing teams with higher limits and audit trail.",
        "rank": 1,
        "amount_paise": 49900,
        "currency": "INR",
        "billing_interval": "monthly",
        "features": {
            "max_seats": 15,
            "max_projects": 50,
            "max_tasks": 2000,
            "max_customers": 500,
            "audit_log": True,
            "advanced_reports": True,
            "sso": False,
        },
    },
    {
        "slug": "business",
        "name": "Business",
        "description": "Scale with SSO-ready entitlements and high limits.",
        "rank": 2,
        "amount_paise": 149900,
        "currency": "INR",
        "billing_interval": "monthly",
        "features": {
            "max_seats": 100,
            "max_projects": 500,
            "max_tasks": 20000,
            "max_customers": 5000,
            "audit_log": True,
            "advanced_reports": True,
            "sso": True,
        },
    },
]


async def seed():
    async with SessionLocal() as db:
        for pdef in PLAN_DEFS:
            plan = await db.scalar(
                select(Plan).where(Plan.slug == pdef["slug"])
            )

            if not plan:
                plan = Plan(
                    slug=pdef["slug"],
                    name=pdef["name"],
                    description=pdef["description"],
                    rank=pdef["rank"],
                    amount_paise=pdef["amount_paise"],
                    currency=pdef["currency"],
                    billing_interval=pdef["billing_interval"],
                )
                db.add(plan)
                await db.flush()

                print(f"Created plan {pdef['slug']}")

            else:
                # Update pricing and plan details without overwriting
                # the Razorpay plan ID created in the Razorpay dashboard.
                plan.name = pdef["name"]
                plan.description = pdef["description"]
                plan.rank = pdef["rank"]
                plan.amount_paise = pdef["amount_paise"]
                plan.currency = pdef["currency"]
                plan.billing_interval = pdef["billing_interval"]

                print(f"Updated plan {pdef['slug']}")

            # Check existing features without triggering lazy loading.
            existing_features = await db.scalars(
                select(PlanFeature).where(
                    PlanFeature.plan_id == plan.id
                )
            )

            existing_keys = {
                feature.feature_key
                for feature in existing_features.all()
            }

            for key, val in pdef["features"].items():
                if key in existing_keys:
                    continue

                if isinstance(val, bool):
                    db.add(
                        PlanFeature(
                            plan_id=plan.id,
                            feature_key=key,
                            enabled=val,
                            limit_value=None,
                        )
                    )
                else:
                    db.add(
                        PlanFeature(
                            plan_id=plan.id,
                            feature_key=key,
                            enabled=True,
                            limit_value=int(val),
                        )
                    )

        # Create demo owner if missing.
        owner = await db.scalar(
            select(User).where(User.email == "owner@flowsuite.com")
        )

        if not owner:
            owner = User(
                email="owner@flowsuite.com",
                password_hash=hash_password("owner123"),
                full_name="Flow Owner",
            )
            db.add(owner)
            await db.flush()
            print("Created owner@flowsuite.com / owner123")

        # Create demo member if missing.
        member = await db.scalar(
            select(User).where(User.email == "member@flowsuite.com")
        )

        if not member:
            member = User(
                email="member@flowsuite.com",
                password_hash=hash_password("member123"),
                full_name="Flow Member",
            )
            db.add(member)
            await db.flush()
            print("Created member@flowsuite.com / member123")

        # Create demo organization if missing.
        org = await db.scalar(
            select(Organization).where(
                Organization.slug == "acme-demo"
            )
        )

        free = await db.scalar(
            select(Plan).where(Plan.slug == "free")
        )

        if not org:
            org = Organization(
                name="Acme Demo",
                slug="acme-demo",
            )
            db.add(org)
            await db.flush()

            db.add(
                Membership(
                    organization_id=org.id,
                    user_id=owner.id,
                    role=Role.owner.value,
                )
            )

            db.add(
                Membership(
                    organization_id=org.id,
                    user_id=member.id,
                    role=Role.member.value,
                )
            )

            if free:
                db.add(
                    Subscription(
                        organization_id=org.id,
                        plan_id=free.id,
                        status="active",
                    )
                )

            print("Created org acme-demo")

        await db.commit()
        print("Seed complete.")


if __name__ == "__main__":
    try:
        asyncio.run(seed())
    except Exception as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        raise
