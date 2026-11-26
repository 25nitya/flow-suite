from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import OrgContext, require_permission
from app.core.models import Customer
from app.core.schemas import CustomerCreate, CustomerOut, CustomerUpdate
from app.modules.audit.service import write_audit
from app.modules.rbac.permissions import CUSTOMER_READ, CUSTOMER_WRITE
from app.modules.usage.service import check_and_increment, recount

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerOut])
async def list_customers(
    ctx: OrgContext = Depends(require_permission(CUSTOMER_READ)),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.scalars(
            select(Customer)
            .where(Customer.organization_id == ctx.organization_id)
            .order_by(Customer.created_at.desc())
        )
    ).all()
    return [CustomerOut.model_validate(r) for r in rows]


@router.post("", response_model=CustomerOut)
async def create_customer(
    body: CustomerCreate,
    ctx: OrgContext = Depends(require_permission(CUSTOMER_WRITE)),
    db: AsyncSession = Depends(get_db),
):
    await check_and_increment(db, ctx.organization_id, "customers")
    row = Customer(
        organization_id=ctx.organization_id,
        name=body.name,
        email=str(body.email) if body.email else None,
        company=body.company,
        notes=body.notes,
    )
    db.add(row)
    await write_audit(
        db,
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        action="customer.create",
        entity_type="customer",
        entity_id=None,
        metadata={"name": body.name},
    )
    await db.commit()
    await db.refresh(row)
    await recount(db, ctx.organization_id, "customers")
    await db.commit()
    return CustomerOut.model_validate(row)


@router.get("/{customer_id}", response_model=CustomerOut)
async def get_customer(
    customer_id: UUID,
    ctx: OrgContext = Depends(require_permission(CUSTOMER_READ)),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(Customer, customer_id)
    if not row or row.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Not found")
    return CustomerOut.model_validate(row)


@router.patch("/{customer_id}", response_model=CustomerOut)
async def update_customer(
    customer_id: UUID,
    body: CustomerUpdate,
    ctx: OrgContext = Depends(require_permission(CUSTOMER_WRITE)),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(Customer, customer_id)
    if not row or row.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, str(v) if k == "email" and v else v)
    await write_audit(
        db,
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        action="customer.update",
        entity_type="customer",
        entity_id=str(row.id),
    )
    await db.commit()
    await db.refresh(row)
    return CustomerOut.model_validate(row)


@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: UUID,
    ctx: OrgContext = Depends(require_permission(CUSTOMER_WRITE)),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(Customer, customer_id)
    if not row or row.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Not found")
    await write_audit(
        db,
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        action="customer.delete",
        entity_type="customer",
        entity_id=str(row.id),
        metadata={"name": row.name},
    )
    await db.delete(row)
    await db.commit()
    await recount(db, ctx.organization_id, "customers")
    await db.commit()
    return {"ok": True}
