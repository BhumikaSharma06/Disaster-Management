"""PostgreSQL-backed token buckets for public coordination submissions."""

import math
from datetime import timedelta
from ipaddress import ip_address

from fastapi import HTTPException, Request, status
from sqlalchemy import case, delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.coordination_rate_limit import CoordinationRateLimit

BURST_CAPACITY = 120
REFILL_PER_SECOND = 2


def _client_address(request: Request) -> str:
    """Use the socket peer address; forwarded headers are not trusted here."""
    host = request.client.host if request.client else "unknown"
    try:
        return str(ip_address(host))
    except ValueError:
        return "unknown"


def enforce_submission_limit(request: Request, db: Session, endpoint: str) -> None:
    """Allow a 120-request burst, then refill two requests per second per endpoint/IP."""
    db.execute(
        delete(CoordinationRateLimit).where(
            CoordinationRateLimit.updated_at < func.now() - timedelta(days=1)
        )
    )
    bucket_key = f"{endpoint}:{_client_address(request)}"
    insert_statement = insert(CoordinationRateLimit).values(
        bucket_key=bucket_key,
        available_tokens=BURST_CAPACITY - 1,
        updated_at=func.now(),
    )
    refilled = func.least(
        BURST_CAPACITY,
        CoordinationRateLimit.available_tokens
        + func.greatest(
            0,
            func.extract("epoch", func.now() - CoordinationRateLimit.updated_at)
            * REFILL_PER_SECOND,
        ),
    )
    statement = insert_statement.on_conflict_do_update(
        index_elements=[CoordinationRateLimit.bucket_key],
        set_={
            "available_tokens": case(
                (refilled >= 1, refilled - 1),
                else_=refilled,
            ),
            "updated_at": func.now(),
        },
    ).returning(CoordinationRateLimit.available_tokens)
    available_tokens = float(db.scalar(statement))
    if available_tokens < 1:
        retry_after = max(1, math.ceil((1 - available_tokens) / REFILL_PER_SECOND))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many coordination submissions. Please retry shortly.",
            headers={"Retry-After": str(retry_after)},
        )
    db.commit()
