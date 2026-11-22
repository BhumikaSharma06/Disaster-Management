"""Super Administrator simulation and audit APIs."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import require_super_admin
from app.core.database import get_db
from app.models.admin_audit import AdminAuditLog
from app.models.disaster_simulation import DisasterSimulation
from app.models.user import User
from app.schemas.super_admin import AdminAuditResponse, SimulationCreate, SimulationResponse
from app.services.admin_audit import record_admin_action

router = APIRouter(prefix="/api/v1/super-admin", tags=["super-admin"])
DatabaseSession = Annotated[Session, Depends(get_db)]
SuperAdminUser = Annotated[User, Depends(require_super_admin)]


@router.get("/simulations", response_model=list[SimulationResponse])
def list_simulations(db: DatabaseSession, admin: SuperAdminUser) -> list[DisasterSimulation]:
    """List current and previous isolated simulation sessions."""
    del admin
    return list(
        db.scalars(
            select(DisasterSimulation).order_by(
                DisasterSimulation.started_at.desc(), DisasterSimulation.id.desc()
            )
        ).all()
    )


@router.post(
    "/simulations",
    response_model=SimulationResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_simulation(
    payload: SimulationCreate,
    db: DatabaseSession,
    admin: SuperAdminUser,
) -> DisasterSimulation:
    """Start the single allowed simulation without creating a live incident."""
    if db.scalar(
        select(DisasterSimulation.id)
        .where(DisasterSimulation.status == "running")
        .with_for_update()
    ) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stop the active simulation before starting another.",
        )
    simulation = DisasterSimulation(
        **payload.model_dump(),
        status="running",
        started_by_user_id=admin.id,
    )
    db.add(simulation)
    try:
        db.flush()
        record_admin_action(
            db,
            admin,
            action="simulation_started",
            target_type="simulation",
            target_id=str(simulation.id),
            target_label=simulation.name,
            details={
                "hazard_type": simulation.hazard_type,
                "area_name": simulation.area_name,
                "severity": simulation.severity,
            },
        )
        db.commit()
        db.refresh(simulation)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another simulation was started. Stop the active simulation before starting another.",
        ) from error
    return simulation


@router.post("/simulations/{simulation_id}/stop", response_model=SimulationResponse)
def stop_simulation(
    simulation_id: int,
    db: DatabaseSession,
    admin: SuperAdminUser,
) -> DisasterSimulation:
    """Stop a running simulation and audit the action."""
    simulation = db.scalar(
        select(DisasterSimulation)
        .where(DisasterSimulation.id == simulation_id)
        .with_for_update()
    )
    if simulation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation was not found.")
    if simulation.status != "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This simulation is already stopped.")
    simulation.status = "stopped"
    simulation.stopped_by_user_id = admin.id
    simulation.ended_at = datetime.now(UTC)
    record_admin_action(
        db,
        admin,
        action="simulation_stopped",
        target_type="simulation",
        target_id=str(simulation.id),
        target_label=simulation.name,
        details={"hazard_type": simulation.hazard_type, "area_name": simulation.area_name},
    )
    db.commit()
    db.refresh(simulation)
    return simulation


@router.get("/audit-logs", response_model=list[AdminAuditResponse])
def list_admin_audit_logs(
    db: DatabaseSession,
    admin: SuperAdminUser,
    limit: int = 100,
) -> list[AdminAuditLog]:
    """Return recent administrative actions to Super Administrators."""
    del admin
    if not 1 <= limit <= 200:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Limit must be between 1 and 200.",
        )
    return list(
        db.scalars(
            select(AdminAuditLog)
            .order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc())
            .limit(limit)
        ).all()
    )
