import uuid
from datetime import datetime

from sqlalchemy import String, Float, DateTime, ForeignKey, Index, text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class ImageCategory(Base):
    __tablename__ = "image_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )

    image = relationship("Image", back_populates="categories")

    __table_args__ = (
        UniqueConstraint("image_id", "category", name="uq_image_category"),
        Index("idx_categories_category", "category"),
        Index("idx_categories_image_id", "image_id"),
    )
