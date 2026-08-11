"""No schema changes are required for literature review reports.

Reports are generated from the current workspace and are intentionally not
persisted in this portfolio MVP. This revision exists as a documented checkpoint
for the feature and keeps migration history explicit.
"""
from alembic import op

revision = "0004_review_metadata"
down_revision = "0003_research_workspace"
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass
