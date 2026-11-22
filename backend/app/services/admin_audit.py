"""Shared helper for writing administrator audit records."""

from typing import Any

from sqlalchemy.orm import Session

from app.models.admin_audit import AdminAuditLog
from app.models.user import User


def record_admin_action(
    db: Session,
    actor: User,
    *,
    action: str,
    target_type: str,
    target_id: str | None = None,
    target_label: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Add an audit record to the caller's transaction."""
    db.add(
        AdminAuditLog(
            actor_user_id=actor.id,
            actor_name=actor.full_name,
            action=action,
            target_type=target_type,
            target_id=target_id,
            target_label=target_label,
            details=details or {},
        )
    )
