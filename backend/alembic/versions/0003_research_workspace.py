from alembic import op
import sqlalchemy as sa

revision = "0003_research_workspace"
down_revision = "0002_library"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "research_workspaces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("research_question", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_research_workspaces_user_id", "research_workspaces", ["user_id"])
    op.create_table(
        "workspace_papers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("research_workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("workspace_id", "paper_id", name="uq_workspace_paper"),
    )
    op.create_index("ix_workspace_papers_workspace_id", "workspace_papers", ["workspace_id"])
    op.create_index("ix_workspace_papers_paper_id", "workspace_papers", ["paper_id"])

def downgrade():
    op.drop_index("ix_workspace_papers_paper_id", table_name="workspace_papers")
    op.drop_index("ix_workspace_papers_workspace_id", table_name="workspace_papers")
    op.drop_table("workspace_papers")
    op.drop_index("ix_research_workspaces_user_id", table_name="research_workspaces")
    op.drop_table("research_workspaces")
