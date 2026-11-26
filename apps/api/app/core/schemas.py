
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=1, max_length=120)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str

    model_config = {"from_attributes": True}


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str


class OrgCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")


class OrgOut(BaseModel):
    id: UUID
    name: str
    slug: str
    role: str | None = None

    model_config = {"from_attributes": True}


class MemberOut(BaseModel):
    user_id: UUID
    email: str
    full_name: str
    role: str


class InviteCreate(BaseModel):
    email: EmailStr
    role: str = "member"


class InviteOut(BaseModel):
    id: UUID
    email: EmailStr
    role: str
    token: str
    expires_at: datetime
    accepted_at: datetime | None

    model_config = {"from_attributes": True}


class InviteAccept(BaseModel):
    token: str


class CustomerCreate(BaseModel):
    name: str
    email: EmailStr | None = None
    company: str | None = None
    notes: str = ""


class CustomerUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    company: str | None = None
    notes: str | None = None


class CustomerOut(BaseModel):
    id: UUID
    name: str
    email: str | None
    company: str | None
    notes: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    customer_id: UUID | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    customer_id: UUID | None = None


class ProjectOut(BaseModel):
    id: UUID
    name: str
    description: str
    status: str
    customer_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    status: str = "todo"
    assignee_id: UUID | None = None
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    assignee_id: UUID | None = None
    due_date: datetime | None = None


class TaskOut(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: str
    status: str
    assignee_id: UUID | None
    due_date: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# Billing schemas

class PlanOut(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str
    rank: int
    features: dict[str, Any]
    amount_paise: int
    currency: str
    billing_interval: str

    model_config = {"from_attributes": True}


class SubscriptionOut(BaseModel):
    plan_slug: str
    plan_name: str
    status: str
    current_period_end: datetime | None
    entitlements: dict[str, Any]
    usage: dict[str, int]


class CheckoutRequest(BaseModel):
    plan_slug: str = Field(pattern=r"^(pro|business)$")


class CheckoutResponse(BaseModel):
    subscription_id: str | None = None
    key_id: str | None = None
    url: str | None = None
    stub: bool = False


class PortalResponse(BaseModel):
    url: str | None = None
    stub: bool = False
    message: str | None = None


class RazorpayVerifyRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_subscription_id: str
    razorpay_signature: str


class AuditOut(BaseModel):
    id: UUID
    action: str
    entity_type: str
    entity_id: str | None
    actor_id: UUID | None
    metadata: dict[str, Any] = Field(validation_alias="metadata_json")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class StubUpgradeRequest(BaseModel):
    plan_slug: str = Field(pattern=r"^(free|pro|business)$")
