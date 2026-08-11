"""add AI analysis cache

Revision ID: 0005_ai_analysis_cache
Revises: 0004_review_metadata
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_ai_analysis_cache"
down_revision = "0004_review_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_analysis_cache",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cache_key", sa.String(length=64), nullable=False),
        sa.Column("analysis_type", sa.String(length=64), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("cache_key", name="uq_ai_analysis_cache_key"),
    )
    op.create_index("ix_ai_analysis_cache_cache_key", "ai_analysis_cache", ["cache_key"], unique=True)
    op.create_index("ix_ai_analysis_cache_analysis_type", "ai_analysis_cache", ["analysis_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ai_analysis_cache_analysis_type", table_name="ai_analysis_cache")
    op.drop_index("ix_ai_analysis_cache_cache_key", table_name="ai_analysis_cache")
    op.drop_table("ai_analysis_cache")
