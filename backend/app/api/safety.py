"""Public and administrator routes for hazard safety tips."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import require_admin
from app.core.database import get_db
from app.models.safety_tip import SafetyTip
from app.models.user import User
from app.schemas.safety import SafetyTipInput, SafetyTipResponse
from app.services.admin_audit import record_admin_action

router = APIRouter(prefix="/api/v1/safety-tips", tags=["safety-tips"])


@router.get("", response_model=list[SafetyTipResponse])
def list_published_safety_tips(
    db: Annotated[Session, Depends(get_db)],
    hazard_type: str | None = Query(default=None, max_length=64),
    phase: str | None = Query(default=None),
    language: str = Query(default="en", max_length=16),
) -> list[SafetyTip]:
    """Return published tips for public safety-guide consumers."""
    statement = select(SafetyTip).where(SafetyTip.status == "published", SafetyTip.language == language)
    if hazard_type:
        statement = statement.where(SafetyTip.hazard_type == hazard_type)
    if phase:
        statement = statement.where(SafetyTip.phase == phase)
    statement = statement.order_by(SafetyTip.hazard_type, SafetyTip.phase, SafetyTip.updated_at.desc())
    return list(db.scalars(statement).all())


@router.get("/admin", response_model=list[SafetyTipResponse])
def list_admin_safety_tips(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
) -> list[SafetyTip]:
    """Return every safety tip for administrator review."""
    del admin
    return list(db.scalars(select(SafetyTip).order_by(SafetyTip.updated_at.desc())).all())


@router.post("/admin", response_model=SafetyTipResponse, status_code=201)
def create_safety_tip(
    payload: SafetyTipInput,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
) -> SafetyTip:
    """Create a draft or published safety tip."""
    tip = SafetyTip(**payload.model_dump())
    db.add(tip)
    db.flush()
    record_admin_action(
        db,
        admin,
        action="safety_tip_created",
        target_type="safety_tip",
        target_id=str(tip.id),
        target_label=tip.title,
        details={"status": tip.status, "hazard_type": tip.hazard_type, "phase": tip.phase},
    )
    db.commit()
    db.refresh(tip)
    return tip


@router.patch("/admin/{tip_id}", response_model=SafetyTipResponse)
def update_safety_tip(
    tip_id: int,
    payload: SafetyTipInput,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
) -> SafetyTip:
    """Replace editable fields and lifecycle status for a safety tip."""
    tip = db.get(SafetyTip, tip_id)
    if tip is None:
        raise HTTPException(status_code=404, detail="Safety tip was not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tip, field, value)
    record_admin_action(
        db,
        admin,
        action="safety_tip_updated",
        target_type="safety_tip",
        target_id=str(tip.id),
        target_label=tip.title,
        details={"status": tip.status, "hazard_type": tip.hazard_type, "phase": tip.phase},
    )
    db.commit()
    db.refresh(tip)
    return tip


@router.delete("/admin/{tip_id}", status_code=204)
def archive_safety_tip(
    tip_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
) -> None:
    """Archive a safety tip instead of deleting it."""
    tip = db.get(SafetyTip, tip_id)
    if tip is None:
        raise HTTPException(status_code=404, detail="Safety tip was not found.")
    tip.status = "archived"
    record_admin_action(
        db,
        admin,
        action="safety_tip_archived",
        target_type="safety_tip",
        target_id=str(tip.id),
        target_label=tip.title,
    )
    db.commit()
