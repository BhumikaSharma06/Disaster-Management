"""Add a dataset registry and quarantined GeoJSON staging records.

Revision ID: 0003_dataset_registry
Revises: 0002_geography_provenance
Create Date: 2026-11-19
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_dataset_registry"
down_revision: str | None = "0002_geography_provenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create import metadata and raw validated feature staging tables."""
    op.create_table(
        "dataset_imports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_key", sa.String(length=100), nullable=False),
        sa.Column("dataset_family", sa.String(length=40), nullable=False),
        sa.Column("evidence_type", sa.String(length=24), nullable=False),
        sa.Column("record_type", sa.String(length=24), nullable=False),
        sa.Column("source_name", sa.String(length=200), nullable=False),
        sa.Column("source_reference", sa.String(length=500), nullable=True),
        sa.Column("source_license", sa.String(length=200), nullable=True),
        sa.Column("attribution", sa.String(length=500), nullable=True),
        sa.Column("coverage", sa.String(length=500), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stale_after_days", sa.Integer(), nullable=True),
        sa.Column(
            "rights_status",
            sa.String(length=16),
            server_default="unconfirmed",
            nullable=False,
        ),
        sa.Column("rights_reference", sa.String(length=500), nullable=True),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("validation_status", sa.String(length=16), nullable=False),
        sa.Column(
            "validation_report",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "review_status",
            sa.String(length=16),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(length=160), nullable=True),
        sa.Column(
            "publication_status",
            sa.String(length=16),
            server_default="quarantined",
            nullable=False,
        ),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "dataset_family IN ('administrative_geography', 'exposure', "
            "'hazard_observations', 'official_warnings', 'flood_extent', "
            "'response_resources', 'road_network', 'community_reports', "
            "'safety_guidance', 'model_outputs', 'other')",
            name="ck_dataset_imports_family",
        ),
        sa.CheckConstraint(
            "evidence_type IN ('geography', 'exposure', 'observation', "
            "'official_warning', 'forecast', 'resource_listing', 'event_report', "
            "'community_report', 'guidance', 'model_output', 'road_network', 'other')",
            name="ck_dataset_imports_evidence_type",
        ),
        sa.CheckConstraint(
            "record_type IN ('regions', 'shelters')",
            name="ck_dataset_imports_record_type",
        ),
        sa.CheckConstraint(
            "(record_type = 'regions' AND dataset_family = 'administrative_geography' "
            "AND evidence_type = 'geography') OR "
            "(record_type = 'shelters' AND dataset_family = 'response_resources' "
            "AND evidence_type = 'resource_listing')",
            name="ck_dataset_imports_record_family",
        ),
        sa.CheckConstraint(
            "validation_status IN ('passed', 'failed')",
            name="ck_dataset_imports_validation_status",
        ),
        sa.CheckConstraint(
            "review_status IN ('pending', 'approved', 'rejected')",
            name="ck_dataset_imports_review_status",
        ),
        sa.CheckConstraint(
            "(review_status = 'pending' AND reviewed_at IS NULL AND reviewed_by IS NULL) "
            "OR (review_status <> 'pending' AND reviewed_at IS NOT NULL "
            "AND reviewed_by IS NOT NULL AND length(trim(reviewed_by)) > 0)",
            name="ck_dataset_imports_review_evidence",
        ),
        sa.CheckConstraint(
            "publication_status IN ('quarantined', 'published', 'withdrawn')",
            name="ck_dataset_imports_publication_status",
        ),
        sa.CheckConstraint(
            "rights_status IN ('unconfirmed', 'documented')",
            name="ck_dataset_imports_rights_status",
        ),
        sa.CheckConstraint(
            "publication_status <> 'published' OR "
            "(review_status = 'approved' AND validation_status = 'passed' "
            "AND rights_status = 'documented')",
            name="ck_dataset_imports_publication_gate",
        ),
        sa.CheckConstraint(
            "rights_status <> 'documented' OR "
            "(rights_reference IS NOT NULL AND length(trim(rights_reference)) > 0)",
            name="ck_dataset_imports_rights_reference",
        ),
        sa.CheckConstraint(
            "length(trim(source_name)) > 0 AND length(trim(coverage)) > 0",
            name="ck_dataset_imports_required_text",
        ),
        sa.CheckConstraint(
            "length(trim(dataset_key)) > 1 AND length(content_sha256) = 64 "
            "AND record_count >= 0",
            name="ck_dataset_imports_identity",
        ),
        sa.CheckConstraint(
            "period_start IS NULL OR period_end IS NULL OR period_start <= period_end",
            name="ck_dataset_imports_period_order",
        ),
        sa.CheckConstraint(
            "stale_after_days IS NULL OR stale_after_days > 0",
            name="ck_dataset_imports_stale_after_positive",
        ),
        sa.UniqueConstraint(
            "dataset_key", "content_sha256", name="uq_dataset_imports_key_digest"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_dataset_imports_imported_at", "dataset_imports", ["imported_at"]
    )
    op.create_table(
        "dataset_import_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_import_id", sa.Integer(), nullable=False),
        sa.Column("source_feature_id", sa.String(length=200), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(trim(source_feature_id)) > 0",
            name="ck_dataset_import_records_source_feature_id",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_import_id"], ["dataset_imports.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dataset_import_id",
            "source_feature_id",
            name="uq_dataset_import_records_feature",
        ),
    )


def downgrade() -> None:
    """Drop staged features and dataset import metadata."""
    op.drop_table("dataset_import_records")
    op.drop_index("ix_dataset_imports_imported_at", table_name="dataset_imports")
    op.drop_table("dataset_imports")
