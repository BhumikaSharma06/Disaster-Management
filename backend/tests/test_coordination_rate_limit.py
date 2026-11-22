"""Tests for shared, batch-friendly coordination submission throttling."""

from typing import Any

import pytest
from fastapi import HTTPException, Request
from sqlalchemy.dialects import postgresql

from app.services.coordination_rate_limit import enforce_submission_limit


class _RateLimitSession:
    def __init__(self, available_tokens: float) -> None:
        self.available_tokens = available_tokens
        self.statement: Any = None
        self.commits = 0
        self.deletes = 0

    def execute(self, statement: Any) -> None:
        del statement
        self.deletes += 1

    def scalar(self, statement: Any) -> float:
        self.statement = statement
        return self.available_tokens

    def commit(self) -> None:
        self.commits += 1


def _request() -> Request:
    return Request({"type": "http", "headers": [], "client": ("192.0.2.9", 4321)})


def test_submission_limit_allows_batch_burst_and_uses_atomic_postgres_bucket() -> None:
    db = _RateLimitSession(available_tokens=118)

    enforce_submission_limit(_request(), db, "supply-offers")

    compiled = db.statement.compile(dialect=postgresql.dialect())
    assert "ON CONFLICT" in str(compiled)
    assert "RETURNING" in str(compiled)
    assert compiled.params["bucket_key"] == "supply-offers:192.0.2.9"
    assert db.commits == 1
    assert db.deletes == 1


def test_submission_limit_returns_retry_after_without_committing_denied_request() -> None:
    db = _RateLimitSession(available_tokens=0.25)

    with pytest.raises(HTTPException) as error:
        enforce_submission_limit(_request(), db, "help-requests")

    assert error.value.status_code == 429
    assert error.value.headers["Retry-After"] == "1"
    assert db.commits == 0
