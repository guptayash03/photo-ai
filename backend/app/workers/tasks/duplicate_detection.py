import logging

from celery import shared_task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.ml.hasher import are_near_duplicates, hamming_distance

logger = logging.getLogger(__name__)

settings = get_settings()
sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
sync_engine = create_engine(sync_db_url)
SyncSession = sessionmaker(bind=sync_engine)


@shared_task(name="app.workers.tasks.duplicate_detection.run_duplicate_scan")
def run_duplicate_scan():
    """Full scan for duplicates across all images."""
    from app.models.image import Image
    from app.models.duplicate import DuplicatePair

    session = SyncSession()
    try:
        images = session.query(Image).filter(
            Image.processing_status == "completed",
            Image.phash.isnot(None),
        ).all()

        new_pairs = 0
        for i, img_a in enumerate(images):
            for img_b in images[i + 1:]:
                # Skip if pair already exists
                existing = (
                    session.query(DuplicatePair)
                    .filter(
                        ((DuplicatePair.image_a_id == img_a.id) & (DuplicatePair.image_b_id == img_b.id))
                        | ((DuplicatePair.image_a_id == img_b.id) & (DuplicatePair.image_b_id == img_a.id))
                    )
                    .first()
                )
                if existing:
                    continue

                # Check exact duplicate
                if img_a.file_md5 and img_a.file_md5 == img_b.file_md5:
                    pair = DuplicatePair(
                        image_a_id=img_a.id,
                        image_b_id=img_b.id,
                        similarity_score=1.0,
                        duplicate_type="exact",
                        detection_method="md5",
                        status="pending",
                    )
                    session.add(pair)
                    new_pairs += 1
                    continue

                # Check near-duplicate via pHash
                if img_a.phash and img_b.phash and are_near_duplicates(img_a.phash, img_b.phash):
                    distance = hamming_distance(img_a.phash, img_b.phash)
                    similarity = 1.0 - (distance / 64.0)
                    pair = DuplicatePair(
                        image_a_id=img_a.id,
                        image_b_id=img_b.id,
                        similarity_score=similarity,
                        duplicate_type="near",
                        detection_method="phash",
                        status="pending",
                    )
                    session.add(pair)
                    new_pairs += 1

        session.commit()
        logger.info(f"Duplicate scan completed: {new_pairs} new pairs found")
    except Exception as e:
        logger.error(f"Duplicate scan failed: {e}")
        session.rollback()
    finally:
        session.close()
