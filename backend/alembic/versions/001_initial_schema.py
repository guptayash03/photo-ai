"""Initial schema with all tables

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Images table
    op.create_table(
        "images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("thumbnail_path", sa.String(1024)),
        sa.Column("file_size", sa.BigInteger, nullable=False),
        sa.Column("mime_type", sa.String(64), nullable=False),
        sa.Column("width", sa.Integer),
        sa.Column("height", sa.Integer),
        sa.Column("taken_at", sa.DateTime(timezone=True)),
        sa.Column("camera_make", sa.String(128)),
        sa.Column("camera_model", sa.String(128)),
        sa.Column("gps_latitude", sa.Float),
        sa.Column("gps_longitude", sa.Float),
        sa.Column("source", sa.String(32), nullable=False, server_default="upload"),
        sa.Column("source_id", sa.String(512)),
        sa.Column("processing_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("phash", sa.String(64)),
        sa.Column("dhash", sa.String(64)),
        sa.Column("average_hash", sa.String(64)),
        sa.Column("file_md5", sa.String(32)),
        sa.Column("embedding", Vector(1408)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_images_phash", "images", ["phash"])
    op.create_index("idx_images_file_md5", "images", ["file_md5"])
    op.create_index("idx_images_processing_status", "images", ["processing_status"])
    op.create_index("idx_images_source", "images", ["source"])
    op.create_index("idx_images_taken_at", "images", ["taken_at"])
    op.create_index("idx_images_created_at", "images", ["created_at"])

    # HNSW index for image embeddings
    op.execute("""
        CREATE INDEX idx_images_embedding_hnsw ON images
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 200)
    """)

    # Face clusters table
    op.create_table(
        "face_clusters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(256)),
        sa.Column("representative_face_id", postgresql.UUID(as_uuid=True)),
        sa.Column("face_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # Faces table
    op.create_table(
        "faces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("image_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("images.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bbox_x", sa.Float, nullable=False),
        sa.Column("bbox_y", sa.Float, nullable=False),
        sa.Column("bbox_width", sa.Float, nullable=False),
        sa.Column("bbox_height", sa.Float, nullable=False),
        sa.Column("embedding", Vector(512), nullable=False),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("face_clusters.id", ondelete="SET NULL")),
        sa.Column("detection_confidence", sa.Float, nullable=False),
        sa.Column("quality_score", sa.Float),
        sa.Column("thumbnail_path", sa.String(1024)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_faces_image_id", "faces", ["image_id"])
    op.create_index("idx_faces_cluster_id", "faces", ["cluster_id"])

    # HNSW index for face embeddings
    op.execute("""
        CREATE INDEX idx_faces_embedding_hnsw ON faces
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 200)
    """)

    # Image categories table
    op.create_table(
        "image_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("image_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("images.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("image_id", "category", name="uq_image_category"),
    )
    op.create_index("idx_categories_category", "image_categories", ["category"])
    op.create_index("idx_categories_image_id", "image_categories", ["image_id"])

    # Duplicate pairs table
    op.create_table(
        "duplicate_pairs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("image_a_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("images.id", ondelete="CASCADE"), nullable=False),
        sa.Column("image_b_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("images.id", ondelete="CASCADE"), nullable=False),
        sa.Column("similarity_score", sa.Float, nullable=False),
        sa.Column("duplicate_type", sa.String(32), nullable=False),
        sa.Column("detection_method", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("image_a_id", "image_b_id", name="uq_duplicate_pair"),
    )
    op.create_index("idx_duplicates_status", "duplicate_pairs", ["status"])

    # Albums table
    op.create_table(
        "albums",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("cover_image_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("images.id", ondelete="SET NULL")),
        sa.Column("image_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # Album images junction table
    op.create_table(
        "album_images",
        sa.Column("album_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("albums.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("image_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("images.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("position", sa.Integer, server_default="0"),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # Processing jobs table
    op.create_table(
        "processing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("total_items", sa.Integer, server_default="0"),
        sa.Column("processed_items", sa.Integer, server_default="0"),
        sa.Column("failed_items", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.Text),
        sa.Column("metadata", postgresql.JSONB),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_jobs_status", "processing_jobs", ["status"])
    op.create_index("idx_jobs_type", "processing_jobs", ["job_type"])


def downgrade() -> None:
    op.drop_table("album_images")
    op.drop_table("albums")
    op.drop_table("processing_jobs")
    op.drop_table("duplicate_pairs")
    op.drop_table("image_categories")
    op.drop_table("faces")
    op.drop_table("face_clusters")
    op.drop_table("images")
    op.execute("DROP EXTENSION IF EXISTS vector")
