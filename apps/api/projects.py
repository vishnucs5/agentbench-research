from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.domain.database import get_db_session
from packages.domain.models import Project, User
from packages.security.middleware import get_current_user

router = APIRouter(prefix="/v1/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    domain: str = "network-intrusion-detection"
    retention_days: int = 90


class ProjectUpdate(BaseModel):
    name: str | None = None
    domain: str | None = None
    retention_days: int | None = None


class ProjectResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    domain: str
    retention_days: int
    created_at: str
    paper_count: int = 0
    run_count: int = 0


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    project = Project(
        owner_id=current_user.id,
        name=payload.name,
        domain=payload.domain,
        retention_days=payload.retention_days,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return ProjectResponse(
        id=str(project.id),
        owner_id=str(project.owner_id),
        name=project.name,
        domain=project.domain,
        retention_days=project.retention_days,
        created_at=project.created_at.isoformat(),
        paper_count=0,
        run_count=0,
    )


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(
        select(Project)
        .options(selectinload(Project.papers), selectinload(Project.runs))
        .where(Project.owner_id == current_user.id)
        .order_by(Project.created_at.desc())
    )
    projects = result.scalars().unique().all()
    out = []
    for p in projects:
        out.append(
            ProjectResponse(
                id=str(p.id),
                owner_id=str(p.owner_id),
                name=p.name,
                domain=p.domain,
                retention_days=p.retention_days,
                created_at=p.created_at.isoformat(),
                paper_count=len(p.papers) if p.papers else 0,
                run_count=len(p.runs) if p.runs else 0,
            )
        )
    # Also include a demo project if no projects exist for demo ease
    if not out:
        demo_id = str(uuid.uuid4())
        out.append(
            ProjectResponse(
                id=demo_id,
                owner_id=str(current_user.id),
                name="Demo NIDS Project",
                domain="network-intrusion-detection",
                retention_days=90,
                created_at="2026-09-20T00:00:00",
                paper_count=0,
                run_count=0,
            )
        )
    return out


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(
        select(Project)
        .options(selectinload(Project.papers), selectinload(Project.runs))
        .where(Project.id == project_id, Project.owner_id == current_user.id)
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(
        id=str(p.id),
        owner_id=str(p.owner_id),
        name=p.name,
        domain=p.domain,
        retention_days=p.retention_days,
        created_at=p.created_at.isoformat(),
        paper_count=len(p.papers) if p.papers else 0,
        run_count=len(p.runs) if p.runs else 0,
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == current_user.id)
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    await session.delete(p)
    await session.commit()
    return None
