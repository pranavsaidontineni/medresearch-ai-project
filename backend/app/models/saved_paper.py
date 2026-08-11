from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class SavedPaper(Base):
    __tablename__ = "saved_papers"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True)
    collection_id: Mapped[int | None] = mapped_column(ForeignKey("collections.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("user_id", "paper_id", name="uq_saved_user_paper"),)
