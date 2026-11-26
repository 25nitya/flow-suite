from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import AuditLog


async def write_audit(
    db: AsyncSession,
    *,
    organization_id: UUID | None,
    actor_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            organization_id=organization_id,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata or {},
        )
    )
