from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20230926_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingest_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_uri", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("artifact_path", sa.String(length=1024), nullable=False),
        sa.Column("artifact_kind", sa.Enum("image", "video", "pdf", "text", "url", name="artifactkind"), nullable=False),
        sa.Column("status", sa.Enum("received", "processing", "completed", "failed", name="ingeststatus"), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("artifact_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )

    op.create_table(
        "entities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ingest_id", sa.Integer(), sa.ForeignKey("ingest_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("normalized", sa.String(length=255), nullable=True),
        sa.Column("context", sa.String(length=255), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
    )
    op.create_index("ix_entities_ingest_id", "entities", ["ingest_id"], unique=False)

    op.create_table(
        "derived_artifacts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ingest_id", sa.Integer(), sa.ForeignKey("ingest_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("artifact_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_derived_ingest", "derived_artifacts", ["ingest_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ingest_id", sa.Integer(), sa.ForeignKey("ingest_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("event", sa.String(length=100), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_audit_ingest", "audit_logs", ["ingest_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_ingest", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_derived_ingest", table_name="derived_artifacts")
    op.drop_table("derived_artifacts")
    op.drop_index("ix_entities_ingest_id", table_name="entities")
    op.drop_table("entities")
    op.drop_table("ingest_jobs")
    op.execute("DROP TYPE IF EXISTS artifactkind")
    op.execute("DROP TYPE IF EXISTS ingeststatus")
