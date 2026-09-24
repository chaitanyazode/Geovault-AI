"""
GeoVault AI - Automated Report Generation API Endpoints (Phase 6B)
Provides permission-scoped endpoints to generate boardroom-grade DOCX and PDF reports,
retrieve report metadata, and securely download generated report documents.
"""

import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.schemas.reports import (
    ReportGenerateRequest,
    ReportMetadataResponse,
)
from app.models.governance import GeneratedReport
from app.services.report_service import ReportGenerationService
from app.security.context import UserContext, AuthorizedScope
from app.security.dependencies import (
    get_current_user,
    get_authorized_scope,
    get_db,
)
from app.security.roles import Permission, has_permission
from app.security.audit import AuditLogger

router = APIRouter(prefix="/reports", tags=["Automated Reports"])
report_service = ReportGenerationService()


@router.get("/", response_model=list)
def list_reports(
    user: UserContext = Depends(get_current_user),
    scope: AuthorizedScope = Depends(get_authorized_scope),
    db: Session = Depends(get_db),
    limit: int = 20,
):
    """
    Returns the most recent generated reports accessible to the current user.
    Only reports covering mines within the user's authorized scope are returned.
    """
    all_reports = db.scalars(
        select(GeneratedReport)
        .order_by(GeneratedReport.created_at.desc())
        .limit(limit * 3)  # over-fetch to allow scope filtering
    ).all()

    results = []
    for rep in all_reports:
        mines_covered = rep.mines_covered or []
        if all(scope.is_mine_permitted(m) for m in mines_covered):
            results.append({
                "report_id": rep.report_id,
                "report_title": rep.report_title,
                "report_type": rep.report_type,
                "mines_covered": mines_covered,
                "reporting_period": rep.reporting_period,
                "generated_at": rep.created_at.strftime("%d-%b-%Y %H:%M:%S IST") if rep.created_at else "",
                "requested_by": rep.user_id,
                "status": rep.status,
                "validation_status": rep.validation_status,
                "evidence_count": rep.evidence_count,
                "conflict_count": rep.conflict_count,
                "pdf_download_url": f"/api/v1/reports/{rep.report_id}/download/pdf" if rep.pdf_filename else None,
                "docx_download_url": f"/api/v1/reports/{rep.report_id}/download/docx" if rep.docx_filename else None,
            })
            if len(results) >= limit:
                break

    return results



@router.post("/generate", response_model=ReportMetadataResponse, status_code=status.HTTP_200_OK)
def generate_report(
    req: ReportGenerateRequest,
    user: UserContext = Depends(get_current_user),
    scope: AuthorizedScope = Depends(get_authorized_scope),
    db: Session = Depends(get_db),
) -> ReportMetadataResponse:
    """
    Generates a structured, publication-grade DOCX & PDF operational report.
    Strictly verifies user authorization scope before retrieving records or generating charts.
    """
    if not (has_permission(user.role, Permission.QUERY_STRUCTURED) or has_permission(user.role, Permission.ADMIN_ALL)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: Role '{user.role}' is not authorized to generate operational reports.",
        )

    res = report_service.generate_report(db=db, user=user, request=req)

    # Audit log report generation
    AuditLogger.log_query(
        db=db,
        user_id=user.user_id,
        question=req.query or f"Report Generation: {res.report_title}",
        route_selected="REPORT",
        scope=scope,
        evidence_count=res.evidence_count,
        evidence_status=res.validation_status,
        response_summary=f"Generated report {res.report_id} covering {res.mines_covered}. Formats: {res.output_formats}",
    )

    return res


@router.get("/{report_id}", response_model=ReportMetadataResponse)
def get_report_metadata(
    report_id: str,
    user: UserContext = Depends(get_current_user),
    scope: AuthorizedScope = Depends(get_authorized_scope),
    db: Session = Depends(get_db),
) -> ReportMetadataResponse:
    """
    Returns metadata for a previously generated report if the requesting user
    is authorized to view all mines covered by the report.
    """
    rep = db.scalar(select(GeneratedReport).where(GeneratedReport.report_id == report_id))
    if not rep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found."
        )

    # Authorization verification
    for m in (rep.mines_covered or []):
        if not scope.is_mine_permitted(m):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Denied: You are not authorized to access reports covering mine '{m}'."
            )

    return ReportMetadataResponse(
        report_id=rep.report_id,
        report_title=rep.report_title,
        report_type=rep.report_type,
        mine_code=rep.mine_code,
        mines_covered=rep.mines_covered or [],
        reporting_period=rep.reporting_period,
        generated_at=rep.created_at.strftime("%d-%b-%Y %H:%M:%S IST") if rep.created_at else "",
        requested_by=rep.user_id,
        status=rep.status,
        output_formats=["DOCX", "PDF"],
        docx_download_url=f"/api/v1/reports/{rep.report_id}/download/docx" if rep.docx_filename else None,
        pdf_download_url=f"/api/v1/reports/{rep.report_id}/download/pdf" if rep.pdf_filename else None,
        evidence_count=rep.evidence_count,
        conflict_count=rep.conflict_count,
        data_gap_count=rep.data_gap_count,
        validation_status=rep.validation_status,
        generation_latency_ms=rep.generation_latency_ms or 0.0,
    )


@router.get("/{report_id}/download")
def download_report_default(
    report_id: str,
    format: str = Query("pdf", description="File format to download: 'pdf' or 'docx'"),
    user: UserContext = Depends(get_current_user),
    scope: AuthorizedScope = Depends(get_authorized_scope),
    db: Session = Depends(get_db),
):
    """Downloads report in requested format (defaults to PDF)."""
    file_path, media_type = report_service.get_report_file(db=db, user=user, report_id=report_id, fmt=format, scope=scope)
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=os.path.basename(file_path),
        content_disposition_type="attachment"
    )


@router.get("/{report_id}/download/docx")
def download_report_docx(
    report_id: str,
    user: UserContext = Depends(get_current_user),
    scope: AuthorizedScope = Depends(get_authorized_scope),
    db: Session = Depends(get_db),
):
    """Direct download for Word document (.docx)."""
    file_path, media_type = report_service.get_report_file(db=db, user=user, report_id=report_id, fmt="docx", scope=scope)
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=os.path.basename(file_path),
        content_disposition_type="attachment"
    )


@router.get("/{report_id}/download/pdf")
def download_report_pdf(
    report_id: str,
    user: UserContext = Depends(get_current_user),
    scope: AuthorizedScope = Depends(get_authorized_scope),
    db: Session = Depends(get_db),
):
    """Direct download for Adobe Acrobat document (.pdf)."""
    file_path, media_type = report_service.get_report_file(db=db, user=user, report_id=report_id, fmt="pdf", scope=scope)
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=os.path.basename(file_path),
        content_disposition_type="attachment"
    )
