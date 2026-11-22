"""Registry metadata and quarantined records for imported datasets."""

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DatasetImport(Base):
    """Provenance, quality, review, and publication state for one import."""

    __tablename__ = "dataset_imports"
    __table_args__ = (
        CheckConstraint(
            "dataset_family IN ('administrative_geography', 'exposure', "
            "'hazard_observations', 'official_warnings', 'flood_extent', "
            "'response_resources', 'road_network', 'community_reports', "
            "'safety_guidance', 'model_outputs', 'other')",
            name="ck_dataset_imports_family",
        ),
        CheckConstraint(
            "evidence_type IN ('geography', 'exposure', 'observation', "
            "'official_warning', 'forecast', 'resource_listing', 'event_report', "
            "'community_report', 'guidance', 'model_output', 'road_network', 'other')",
            name="ck_dataset_imports_evidence_type",
        ),
        CheckConstraint(
            "record_type IN ('regions', 'shelters')",
            name="ck_dataset_imports_record_type",
        ),
        CheckConstraint(
            "(record_type = 'regions' AND dataset_family = 'administrative_geography' "
            "AND evidence_type = 'geography') OR "
            "(record_type = 'shelters' AND dataset_family = 'response_resources' "
            "AND evidence_type = 'resource_listing')",
            name="ck_dataset_imports_record_family",
        ),
        CheckConstraint(
            "validation_status IN ('passed', 'failed')",
            name="ck_dataset_imports_validation_status",
        ),
        CheckConstraint(
            "review_status IN ('pending', 'approved', 'rejected')",
            name="ck_dataset_imports_review_status",
        ),
        CheckConstraint(
            "(review_status = 'pending' AND reviewed_at IS NULL AND reviewed_by IS NULL) "
            "OR (review_status <> 'pending' AND reviewed_at IS NOT NULL "
            "AND reviewed_by IS NOT NULL AND length(trim(reviewed_by)) > 0)",
            name="ck_dataset_imports_review_evidence",
        ),
        CheckConstraint(
            "publication_status IN ('quarantined', 'published', 'withdrawn')",
            name="ck_dataset_imports_publication_status",
        ),
        CheckConstraint(
            "rights_status IN ('unconfirmed', 'documented')",
            name="ck_dataset_imports_rights_status",
        ),
        CheckConstraint(
            "publication_status <> 'published' OR "
            "(review_status = 'approved' AND validation_status = 'passed' "
            "AND rights_status = 'documented')",
            name="ck_dataset_imports_publication_gate",
        ),
        CheckConstraint(
            "rights_status <> 'documented' OR "
            "(rights_reference IS NOT NULL AND length(trim(rights_reference)) > 0)",
            name="ck_dataset_imports_rights_reference",
        ),
        CheckConstraint(
            "length(trim(source_name)) > 0 AND length(trim(coverage)) > 0",
            name="ck_dataset_imports_required_text",
        ),
        CheckConstraint(
            "length(trim(dataset_key)) > 1 AND length(content_sha256) = 64 AND record_count >= 0",
            name="ck_dataset_imports_identity",
        ),
        CheckConstraint(
            "period_start IS NULL OR period_end IS NULL OR period_start <= period_end",
            name="ck_dataset_imports_period_order",
        ),
        CheckConstraint(
            "stale_after_days IS NULL OR stale_after_days > 0",
            name="ck_dataset_imports_stale_after_positive",
        ),
        UniqueConstraint("dataset_key", "content_sha256", name="uq_dataset_imports_key_digest"),
        Index("ix_dataset_imports_imported_at", "imported_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_key: Mapped[str] = mapped_column(String(100), nullable=False)
    dataset_family: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(24), nullable=False)
    record_type: Mapped[str] = mapped_column(String(24), nullable=False)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(500))
    source_license: Mapped[str | None] = mapped_column(String(200))
    attribution: Mapped[str | None] = mapped_column(String(500))
    coverage: Mapped[str] = mapped_column(String(500), nullable=False)
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stale_after_days: Mapped[int | None] = mapped_column(Integer)
    rights_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="unconfirmed",
        server_default="unconfirmed",
    )
    rights_reference: Mapped[str | None] = mapped_column(String(500))
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(16), nullable=False)
    validation_report: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    review_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[str | None] = mapped_column(String(160))
    publication_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="quarantined",
        server_default="quarantined",
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    records: Mapped[list["DatasetImportRecord"]] = relationship(
        back_populates="dataset_import",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class DatasetImportRecord(Base):
    """A validated source feature retained in quarantine as original JSON."""

    __tablename__ = "dataset_import_records"
    __table_args__ = (
        UniqueConstraint(
            "dataset_import_id",
            "source_feature_id",
            name="uq_dataset_import_records_feature",
        ),
        CheckConstraint(
            "length(trim(source_feature_id)) > 0",
            name="ck_dataset_import_records_source_feature_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_import_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_imports.id", ondelete="CASCADE"), nullable=False
    )
    source_feature_id: Mapped[str] = mapped_column(String(200), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    dataset_import: Mapped[DatasetImport] = relationship(back_populates="records")
