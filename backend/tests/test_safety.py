"""Published safety guidance API tests."""

from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models.safety_tip import SafetyTip


def test_public_safety_guidance_includes_only_published_matching_language() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SafetyTip.__table__.create(engine)
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db() -> Iterator[Session]:
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with test_session() as db:
            db.add_all(
                [
                    SafetyTip(
                        title="Flood before",
                        content="Follow local safety instructions.",
                        hazard_type="flood",
                        phase="before",
                        language="en",
                        status="published",
                    ),
                    SafetyTip(
                        title="Draft flood",
                        content="Draft content is not public.",
                        hazard_type="flood",
                        phase="during",
                        language="en",
                        status="draft",
                    ),
                    SafetyTip(
                        title="Hindi flood",
                        content="Hindi content is not returned for English.",
                        hazard_type="flood",
                        phase="after",
                        language="hi",
                        status="published",
                    ),
                    SafetyTip(
                        title="Cyclone before",
                        content="Cyclone content.",
                        hazard_type="cyclone",
                        phase="before",
                        language="en",
                        status="published",
                    ),
                ]
            )
            db.commit()

        response = TestClient(app).get("/api/v1/safety-tips?language=en&hazard_type=flood")

        assert response.status_code == 200
        assert [tip["title"] for tip in response.json()] == ["Flood before"]
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
