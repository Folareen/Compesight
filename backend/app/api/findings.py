import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.models.finding import ChangeType, Finding, Urgency
from app.repositories import competitors as competitors_repo
from app.repositories import finding_feedback as finding_feedback_repo
from app.repositories import findings as findings_repo
from app.schemas.finding import FindingListOut, FindingOut
from app.schemas.finding_feedback import FindingFeedbackIn, FindingFeedbackOut

router = APIRouter(prefix="/findings", tags=["findings"])


def _to_finding_out(finding: Finding) -> FindingOut:
    return FindingOut(
        id=finding.id,
        competitor_id=finding.competitor_id,
        source_id=finding.source_id,
        snapshot_id=finding.snapshot_id,
        change_type=finding.change_type,
        urgency=finding.urgency,
        title=finding.title,
        summary=finding.summary,
        changeset=finding.changeset.get("fields", []),
        is_baseline=finding.is_baseline,
        classification_status=finding.classification_status,
        detected_at=finding.detected_at,
    )


@router.get("", response_model=FindingListOut)
async def list_findings(
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
    competitor_id: uuid.UUID | None = Query(default=None),
    change_type: ChangeType | None = Query(default=None),
    urgency: Urgency | None = Query(default=None),
    since: datetime | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
) -> FindingListOut:
    if competitor_id is not None:
        # A competitor_id in a query param is exactly as untrusted as one
        # in a path segment — must be confirmed against this workspace.
        competitor = await competitors_repo.get(db, ctx.workspace_id, competitor_id)
        if competitor is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "competitor not found")

    findings, next_cursor = await findings_repo.list_for_workspace(
        db,
        ctx.workspace_id,
        competitor_id=competitor_id,
        change_type=change_type,
        urgency=urgency,
        since=since,
        cursor=cursor,
        limit=limit,
    )
    return FindingListOut(
        data=[_to_finding_out(f) for f in findings], next_cursor=next_cursor, has_more=next_cursor is not None
    )


@router.get("/{finding_id}", response_model=FindingOut)
async def get_finding(
    finding_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> FindingOut:
    finding = await findings_repo.get(db, ctx.workspace_id, finding_id)
    if finding is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "finding not found")
    return _to_finding_out(finding)


@router.post("/{finding_id}/feedback", response_model=FindingFeedbackOut, status_code=status.HTTP_201_CREATED)
async def create_finding_feedback(
    finding_id: uuid.UUID,
    body: FindingFeedbackIn,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db),
) -> FindingFeedbackOut:
    finding = await findings_repo.get(db, ctx.workspace_id, finding_id)
    if finding is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "finding not found")

    feedback = await finding_feedback_repo.create(
        db,
        ctx.workspace_id,
        finding_id,
        ctx.user_id,
        body.verdict,
        body.corrected_change_type,
        body.corrected_urgency,
    )
    await db.commit()
    return FindingFeedbackOut(
        id=feedback.id,
        finding_id=feedback.finding_id,
        verdict=feedback.verdict,
        corrected_change_type=feedback.corrected_change_type,
        corrected_urgency=feedback.corrected_urgency,
        created_at=feedback.created_at,
    )
