import uuid
from datetime import datetime

from sqlalchemy import String, Float, DateTime, ForeignKey, Index, text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class DuplicatePair(Base):
    __tablename__ = "duplicate_pairs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    image_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), nullable=False
    )
    image_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), nullable=False
    )
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    duplicate_type: Mapped[str] = mapped_column(String(32), nullable=False)
    detection_method: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )

    image_a = relationship("Image", foreign_keys=[image_a_id])
    image_b = relationship("Image", foreign_keys=[image_b_id])

    __table_args__ = (
        UniqueConstraint("image_a_id", "image_b_id", name="uq_duplicate_pair"),
        Index("idx_duplicates_status", "status"),
    )
