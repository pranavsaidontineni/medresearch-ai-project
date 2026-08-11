from alembic import op
import sqlalchemy as sa
revision = "0002_library"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("collections", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(120), nullable=False), sa.Column("description", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("user_id", "name", name="uq_collection_user_name"))
    op.create_index("ix_collections_user_id", "collections", ["user_id"])
    op.create_table("saved_papers", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False), sa.Column("collection_id", sa.Integer(), sa.ForeignKey("collections.id", ondelete="SET NULL"), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("user_id", "paper_id", name="uq_saved_user_paper"))
    op.create_index("ix_saved_papers_user_id", "saved_papers", ["user_id"]); op.create_index("ix_saved_papers_paper_id", "saved_papers", ["paper_id"]); op.create_index("ix_saved_papers_collection_id", "saved_papers", ["collection_id"])
    op.create_table("search_history", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("query", sa.String(300), nullable=False), sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.create_index("ix_search_history_user_id", "search_history", ["user_id"])

def downgrade():
    op.drop_index("ix_search_history_user_id", table_name="search_history"); op.drop_table("search_history")
    op.drop_index("ix_saved_papers_collection_id", table_name="saved_papers"); op.drop_index("ix_saved_papers_paper_id", table_name="saved_papers"); op.drop_index("ix_saved_papers_user_id", table_name="saved_papers"); op.drop_table("saved_papers")
    op.drop_index("ix_collections_user_id", table_name="collections"); op.drop_table("collections")
