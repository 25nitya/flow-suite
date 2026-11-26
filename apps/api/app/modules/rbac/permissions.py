"""RBAC permission constants and role maps."""

from enum import Enum


class Role(str, Enum):
    owner = "owner"
    admin = "admin"
    member = "member"
    viewer = "viewer"


# permission keys
CUSTOMER_READ = "customer:read"
CUSTOMER_WRITE = "customer:write"
PROJECT_READ = "project:read"
PROJECT_WRITE = "project:write"
TASK_READ = "task:read"
TASK_WRITE = "task:write"
MEMBER_READ = "member:read"
MEMBER_INVITE = "member:invite"
MEMBER_MANAGE = "member:manage"
BILLING_MANAGE = "billing:manage"
AUDIT_READ = "audit:read"
ORG_MANAGE = "org:manage"

ROLE_PERMISSIONS: dict[str, set[str]] = {
    Role.owner.value: {
        CUSTOMER_READ,
        CUSTOMER_WRITE,
        PROJECT_READ,
        PROJECT_WRITE,
        TASK_READ,
        TASK_WRITE,
        MEMBER_READ,
        MEMBER_INVITE,
        MEMBER_MANAGE,
        BILLING_MANAGE,
        AUDIT_READ,
        ORG_MANAGE,
    },
    Role.admin.value: {
        CUSTOMER_READ,
        CUSTOMER_WRITE,
        PROJECT_READ,
        PROJECT_WRITE,
        TASK_READ,
        TASK_WRITE,
        MEMBER_READ,
        MEMBER_INVITE,
        MEMBER_MANAGE,
        AUDIT_READ,
        ORG_MANAGE,
    },
    Role.member.value: {
        CUSTOMER_READ,
        CUSTOMER_WRITE,
        PROJECT_READ,
        PROJECT_WRITE,
        TASK_READ,
        TASK_WRITE,
        MEMBER_READ,
    },
    Role.viewer.value: {
        CUSTOMER_READ,
        PROJECT_READ,
        TASK_READ,
        MEMBER_READ,
    },
}


def role_has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
