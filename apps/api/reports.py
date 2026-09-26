from __future__ import annotations

from datetime import datetime, UTC
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.domain.database import get_db_session
from packages.domain.models import Claim, EvidenceLink, Paper, PlagiarismCheck, Project, ResearchRun, User
from packages.plagiarism.service import PlagiarismService, get_plagiarism_service
from packages.reports.generators.audit import generate_claim_audit_log
from packages.reports.generators.bibtex import generate_bibtex
from packages.reports.generators.latex import generate_latex_manuscript
from packages.reports.generators.markdown import generate_markdown_survey
from packages.reports.generators.plagiarism_cert import generate_plagiarism_certificate
from packages.security.middleware import get_current_user

router = APIRouter(prefix="/v1/reports", tags=["reports"])


class ReportPreviewRequest(BaseModel):
    project_id: UUID
    report_type: Literal["bibtex", "latex", "markdown", "audit"]
    custom_title: str | None = None


class ReportPreviewResponse(BaseModel):
    project_id: str
    report_type: str
    filename: str
    content: str
    char_count: int
    line_count: int
    generated_at: str


class PlagiarismExportResponse(BaseModel):
    check_id: str
    format: str
    filename: str
    content: str


async def _require_owned_project(
    session: AsyncSession, project_id: UUID, current_user: User
) -> Project:
    stmt = (
        select(Project)
        .where(Project.id == project_id, Project.owner_id == current_user.id)
    )
    result = await session.execute(stmt)
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found or access denied",
        )
    return project


async def _build_report_content(
    session: AsyncSession,
    project: Project,
    report_type: str,
    custom_title: str | None = None,
) -> tuple[str, str, str]:
    """Returns (content, filename, media_type)."""
    # Fetch papers
    papers_stmt = select(Paper).where(Paper.project_id == project.id).order_by(Paper.created_at.desc())
    papers = (await session.execute(papers_stmt)).scalars().all()

    # Fetch runs
    runs_stmt = select(ResearchRun).where(ResearchRun.project_id == project.id).order_by(ResearchRun.started_at.desc())
    runs = (await session.execute(runs_stmt)).scalars().all()

    safe_name = "".join(c if c.isalnum() else "_" for c in project.name.lower()).strip("_") or "report"

    if report_type == "bibtex":
        content = generate_bibtex(papers)
        filename = f"references_{safe_name}.bib"
        media_type = "application/x-bibtex; charset=utf-8"

    elif report_type == "latex":
        content = generate_latex_manuscript(
            project=project,
            papers=papers,
            runs=runs,
            custom_title=custom_title,
        )
        filename = f"manuscript_{safe_name}.tex"
        media_type = "application/x-tex; charset=utf-8"

    elif report_type == "markdown":
        content = generate_markdown_survey(
            project=project,
            papers=papers,
            runs=runs,
        )
        filename = f"literature_survey_{safe_name}.md"
        media_type = "text/markdown; charset=utf-8"

    elif report_type == "audit":
        claims_stmt = (
            select(Claim, EvidenceLink)
            .join(Paper, Claim.paper_id == Paper.id)
            .outerjoin(EvidenceLink, Claim.id == EvidenceLink.claim_id)
            .where(Paper.project_id == project.id)
        )
        rows = (await session.execute(claims_stmt)).all()

        claims_list: list[dict[str, Any]] = []
        verifications_list: list[dict[str, Any]] = []
        seen_claim_ids = set()

        for claim, link in rows:
            if claim.id not in seen_claim_ids:
                seen_claim_ids.add(claim.id)
                claims_list.append({
                    "claim_id": str(claim.id),
                    "claim_text": claim.claim_text,
                    "claim_type": claim.claim_type,
                    "confidence": claim.confidence,
                    "status": claim.status.value if hasattr(claim.status, "value") else str(claim.status),
                })
            if link is not None:
                verifications_list.append({
                    "claim_id": str(claim.id),
                    "evidence_id": str(link.chunk_id),
                    "status": link.support_type.value if hasattr(link.support_type, "value") else str(link.support_type),
                    "confidence": link.match_score,
                    "page": link.page_number,
                })

        content = generate_claim_audit_log(
            project_name=project.name,
            claims=claims_list,
            verifications=verifications_list,
        )
        filename = f"claim_audit_log_{safe_name}.md"
        media_type = "text/markdown; charset=utf-8"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported report type '{report_type}'. Choose from bibtex, latex, markdown, audit.",
        )

    return content, filename, media_type


@router.get("/projects/{project_id}/export")
async def export_project_report(
    project_id: UUID,
    type: Literal["bibtex", "latex", "markdown", "audit"] = Query("markdown", description="Type of report to export"),
    format: Literal["file", "json"] = Query("file", description="Download as attachment file or return JSON payload"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """Export structured report for a research project."""
    project = await _require_owned_project(session, project_id, current_user)
    content, filename, media_type = await _build_report_content(session, project, type)

    if format == "json":
        return {
            "project_id": str(project_id),
            "report_type": type,
            "filename": filename,
            "content": content,
            "char_count": len(content),
            "generated_at": datetime.now(UTC).isoformat(),
        }

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/preview", response_model=ReportPreviewResponse)
async def preview_project_report(
    payload: ReportPreviewRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ReportPreviewResponse:
    """Generate in-memory preview of report content without file download."""
    project = await _require_owned_project(session, payload.project_id, current_user)
    content, filename, _ = await _build_report_content(
        session, project, payload.report_type, payload.custom_title
    )

    return ReportPreviewResponse(
        project_id=str(payload.project_id),
        report_type=payload.report_type,
        filename=filename,
        content=content,
        char_count=len(content),
        line_count=len(content.splitlines()),
        generated_at=datetime.now(UTC).isoformat(),
    )


@router.get("/plagiarism/{check_id}/export")
async def export_plagiarism_certificate(
    check_id: UUID,
    format: Literal["html", "md", "json"] = Query("html", description="Certificate format: html, md, or json"),
    current_user: User = Depends(get_current_user),
    service: PlagiarismService = Depends(get_plagiarism_service),
) -> Any:
    """Export academic originality certificate for a plagiarism check."""
    check = await service.get_check_result(check_id, current_user.id)
    if check is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plagiarism check {check_id} not found or access denied",
        )

    matches = await service.get_check_matches(check_id, current_user.id)
    fmt = "md" if format == "md" else "html"
    content = generate_plagiarism_certificate(check=check, matches=matches, format_type=fmt)
    filename = f"originality_certificate_{check_id}.{'md' if fmt == 'md' else 'html'}"

    if format == "json":
        return PlagiarismExportResponse(
            check_id=str(check_id),
            format=format,
            filename=filename,
            content=content,
        )

    media_type = "text/markdown; charset=utf-8" if fmt == "md" else "text/html; charset=utf-8"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'} if fmt == "md" else {}

    return Response(
        content=content,
        media_type=media_type,
        headers=headers,
    )
