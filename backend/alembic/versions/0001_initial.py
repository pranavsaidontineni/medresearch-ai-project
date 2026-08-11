from alembic import op
import sqlalchemy as sa
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("email", sa.String(length=320), nullable=False), sa.Column("password_hash", sa.String(length=255), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("papers", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("pmid", sa.String(length=32), nullable=False), sa.Column("title", sa.Text(), nullable=False), sa.Column("abstract", sa.Text(), nullable=True), sa.Column("journal", sa.String(length=500), nullable=True), sa.Column("publication_date", sa.String(length=50), nullable=True), sa.Column("doi", sa.String(length=255), nullable=True), sa.Column("authors_json", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.create_index("ix_papers_pmid", "papers", ["pmid"], unique=True)

def downgrade():
    op.drop_index("ix_papers_pmid", table_name="papers")
    op.drop_table("papers")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
