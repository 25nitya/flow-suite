from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import OrgContext, require_permission
from app.core.models import Project, Task
from app.core.schemas import (
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)
from app.modules.audit.service import write_audit
from app.modules.rbac.permissions import PROJECT_READ, PROJECT_WRITE, TASK_READ, TASK_WRITE
from app.modules.usage.service import check_and_increment, recount

router = APIRouter(tags=["projects"])


@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(
    ctx: OrgContext = Depends(require_permission(PROJECT_READ)),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.scalars(
            select(Project)
            .where(Project.organization_id == ctx.organization_id)
            .order_by(Project.created_at.desc())
        )
    ).all()
    return [ProjectOut.model_validate(r) for r in rows]


@router.post("/projects", response_model=ProjectOut)
async def create_project(
    body: ProjectCreate,
    ctx: OrgContext = Depends(require_permission(PROJECT_WRITE)),
    db: AsyncSession = Depends(get_db),
):
    await check_and_increment(db, ctx.organization_id, "projects")
    row = Project(
        organization_id=ctx.organization_id,
        name=body.name,
        description=body.description,
        customer_id=body.customer_id,
    )
    db.add(row)
    await write_audit(
        db,
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        action="project.create",
        entity_type="project",
        metadata={"name": body.name},
    )
    await db.commit()
    await db.refresh(row)
    await recount(db, ctx.organization_id, "projects")
    await db.commit()
    return ProjectOut.model_validate(row)


@router.patch("/projects/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    ctx: OrgContext = Depends(require_permission(PROJECT_WRITE)),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(Project, project_id)
    if not row or row.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await write_audit(
        db,
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        action="project.update",
        entity_type="project",
        entity_id=str(row.id),
    )
    await db.commit()
    await db.refresh(row)
    return ProjectOut.model_validate(row)


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: UUID,
    ctx: OrgContext = Depends(require_permission(PROJECT_WRITE)),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(Project, project_id)
    if not row or row.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Not found")
    await write_audit(
        db,
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        action="project.delete",
        entity_type="project",
        entity_id=str(row.id),
        metadata={"name": row.name},
    )
    await db.delete(row)
    await db.commit()
    await recount(db, ctx.organization_id, "projects")
    await recount(db, ctx.organization_id, "tasks")
    await db.commit()
    return {"ok": True}


@router.get("/projects/{project_id}/tasks", response_model=list[TaskOut])
async def list_tasks(
    project_id: UUID,
    ctx: OrgContext = Depends(require_permission(TASK_READ)),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Project not found")
    rows = (
        await db.scalars(
            select(Task).where(Task.project_id == project_id).order_by(Task.created_at.desc())
        )
    ).all()
    return [TaskOut.model_validate(r) for r in rows]


@router.post("/projects/{project_id}/tasks", response_model=TaskOut)
async def create_task(
    project_id: UUID,
    body: TaskCreate,
    ctx: OrgContext = Depends(require_permission(TASK_WRITE)),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await check_and_increment(db, ctx.organization_id, "tasks")
    row = Task(
        organization_id=ctx.organization_id,
        project_id=project_id,
        title=body.title,
        description=body.description,
        status=body.status,
        assignee_id=body.assignee_id,
        due_date=body.due_date,
    )
    db.add(row)
    await write_audit(
        db,
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        action="task.create",
        entity_type="task",
        metadata={"title": body.title, "project_id": str(project_id)},
    )
    await db.commit()
    await db.refresh(row)
    await recount(db, ctx.organization_id, "tasks")
    await db.commit()
    return TaskOut.model_validate(row)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: UUID,
    body: TaskUpdate,
    ctx: OrgContext = Depends(require_permission(TASK_WRITE)),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(Task, task_id)
    if not row or row.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await write_audit(
        db,
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        action="task.update",
        entity_type="task",
        entity_id=str(row.id),
    )
    await db.commit()
    await db.refresh(row)
    return TaskOut.model_validate(row)


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: UUID,
    ctx: OrgContext = Depends(require_permission(TASK_WRITE)),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(Task, task_id)
    if not row or row.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Not found")
    await write_audit(
        db,
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        action="task.delete",
        entity_type="task",
        entity_id=str(row.id),
        metadata={"title": row.title},
    )
    await db.delete(row)
    await db.commit()
    await recount(db, ctx.organization_id, "tasks")
    await db.commit()
    return {"ok": True}
