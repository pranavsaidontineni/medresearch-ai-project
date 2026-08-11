"""persist generated research reports

Revision ID: 0006_research_reports
Revises: 0005_ai_analysis_cache
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_research_reports"
down_revision = "0005_ai_analysis_cache"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "research_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("research_workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("report_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_research_reports_user_id", "research_reports", ["user_id"])
    op.create_index("ix_research_reports_workspace_id", "research_reports", ["workspace_id"])

def downgrade() -> None:
    op.drop_index("ix_research_reports_workspace_id", table_name="research_reports")
    op.drop_index("ix_research_reports_user_id", table_name="research_reports")
    op.drop_table("research_reports")
