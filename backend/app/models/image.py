import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import String, Integer, BigInteger, Float, DateTime, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Image(Base):
    __tablename__ = "images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    thumbnail_path: Mapped[str | None] = mapped_column(String(1024))
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)

    # EXIF metadata
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    camera_make: Mapped[str | None] = mapped_column(String(128))
    camera_model: Mapped[str | None] = mapped_column(String(128))
    gps_latitude: Mapped[float | None] = mapped_column(Float)
    gps_longitude: Mapped[float | None] = mapped_column(Float)

    # Source tracking
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="upload")
    source_id: Mapped[str | None] = mapped_column(String(512))

    # Processing state
    processing_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )

    # Hashes for duplicate detection
    phash: Mapped[str | None] = mapped_column(String(64))
    dhash: Mapped[str | None] = mapped_column(String(64))
    average_hash: Mapped[str | None] = mapped_column(String(64))
    file_md5: Mapped[str | None] = mapped_column(String(32))

    # CLIP/Vertex AI embedding
    embedding = mapped_column(Vector(1408), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), onupdate=datetime.utcnow
    )

    # Relationships
    categories = relationship("ImageCategory", back_populates="image", cascade="all, delete-orphan")
    faces = relationship("Face", back_populates="image", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_images_phash", "phash"),
        Index("idx_images_file_md5", "file_md5"),
        Index("idx_images_processing_status", "processing_status"),
        Index("idx_images_source", "source"),
        Index("idx_images_taken_at", "taken_at"),
        Index("idx_images_created_at", "created_at"),
    )
