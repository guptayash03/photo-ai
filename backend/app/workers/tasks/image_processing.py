import io
import uuid
import logging
from datetime import datetime, timezone

from PIL import Image
from celery import shared_task
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.ml.hasher import compute_file_md5, compute_phash, compute_dhash, compute_average_hash
from app.ml.embedding_provider import get_embedding_provider
from app.ml.face_analyzer import FaceAnalyzer
from app.ml.categorizer import ImageCategorizer
from app.core.storage import get_storage

logger = logging.getLogger(__name__)

settings = get_settings()
sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
sync_engine = create_engine(sync_db_url)
SyncSession = sessionmaker(bind=sync_engine)


def get_sync_session():
    return SyncSession()


@shared_task(name="app.workers.tasks.image_processing.process_image_pipeline")
def process_image_pipeline(image_id: str):
    """Full processing pipeline for a single image."""
    from app.models.image import Image as ImageModel
    from app.models.face import Face, FaceCluster
    from app.models.category import ImageCategory

    session = get_sync_session()
    try:
        image = session.query(ImageModel).filter(ImageModel.id == uuid.UUID(image_id)).first()
        if not image:
            logger.error(f"Image {image_id} not found")
            return

        image.processing_status = "processing"
        session.commit()

        # Download image from storage
        storage = get_storage()
        parts = image.storage_path.split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid storage path: {image.storage_path}")

        import asyncio
        loop = asyncio.new_event_loop()
        image_bytes = loop.run_until_complete(storage.download(parts[0], parts[1]))

        # === STAGE 1: Preprocessing ===
        _preprocess_image(session, image, image_bytes, storage, loop)

        # === STAGE 2: Hashing ===
        _compute_hashes(session, image, image_bytes)

        # === STAGE 3: Embeddings ===
        _generate_embedding(session, image, image_bytes, loop)

        # === STAGE 4: Categorization ===
        _categorize_image(session, image, image_bytes, loop)

        # === STAGE 5: Face Detection ===
        _detect_faces(session, image, image_bytes, storage, loop)

        # === STAGE 6: Duplicate Detection ===
        _check_duplicates(session, image)

        # Mark as completed
        image.processing_status = "completed"
        session.commit()
        logger.info(f"Image {image_id} processing completed")

    except Exception as e:
        logger.error(f"Pipeline failed for image {image_id}: {e}")
        try:
            image.processing_status = "failed"
            session.commit()
        except Exception:
            session.rollback()
    finally:
        session.close()
        if 'loop' in locals():
            loop.close()


def _preprocess_image(session, image, image_bytes: bytes, storage, loop):
    """Generate thumbnail and extract EXIF metadata."""
    from app.utils.image_utils import generate_thumbnail, extract_exif

    # Generate thumbnail
    thumbnail_bytes = generate_thumbnail(image_bytes)
    thumbnail_key = f"{image.id}/thumbnail.jpg"
    loop.run_until_complete(
        storage.upload("thumbnails", thumbnail_key, thumbnail_bytes, "image/jpeg")
    )
    image.thumbnail_path = f"thumbnails/{thumbnail_key}"

    # Extract dimensions and EXIF
    img = Image.open(io.BytesIO(image_bytes))
    image.width = img.width
    image.height = img.height

    exif_data = extract_exif(image_bytes)
    if exif_data:
        image.taken_at = exif_data.get("taken_at")
        image.camera_make = exif_data.get("camera_make")
        image.camera_model = exif_data.get("camera_model")
        image.gps_latitude = exif_data.get("gps_latitude")
        image.gps_longitude = exif_data.get("gps_longitude")

    session.commit()


def _compute_hashes(session, image, image_bytes: bytes):
    """Compute perceptual and file hashes."""
    image.file_md5 = compute_file_md5(image_bytes)
    image.phash = compute_phash(image_bytes)
    image.dhash = compute_dhash(image_bytes)
    image.average_hash = compute_average_hash(image_bytes)
    session.commit()


def _generate_embedding(session, image, image_bytes: bytes, loop):
    """Generate Vertex AI / CLIP embedding."""
    try:
        provider = get_embedding_provider()
        embedding = loop.run_until_complete(provider.embed_image(image_bytes))
        # Cast to Python floats — psycopg2 cannot adapt numpy.float32
        image.embedding = [float(x) for x in embedding]
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"Embedding generation failed for {image.id}: {e}")


def _categorize_image(session, image, image_bytes: bytes, loop):
    """Categorize using Gemini Vision."""
    from app.models.category import ImageCategory

    try:
        categorizer = ImageCategorizer()
        category, confidence = loop.run_until_complete(categorizer.categorize(image_bytes))

        cat_entry = ImageCategory(
            image_id=image.id,
            category=category,
            confidence=confidence,
            model_version=settings.GEMINI_MODEL,
        )
        session.add(cat_entry)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"Categorization failed for {image.id}: {e}")


def _detect_faces(session, image, image_bytes: bytes, storage, loop):
    """Detect faces and assign to clusters."""
    from app.models.face import Face, FaceCluster
    import numpy as np

    try:
        analyzer = FaceAnalyzer()
        detected_faces = analyzer.detect_faces(image_bytes)

        for detected in detected_faces:
            if detected.confidence < 0.5:
                continue

            # Crop and store face thumbnail
            face_crop = analyzer.crop_face(image_bytes, detected.bbox)
            face_id = uuid.uuid4()
            face_key = f"{face_id}.jpg"
            loop.run_until_complete(
                storage.upload("faces", face_key, face_crop, "image/jpeg")
            )

            # Find matching cluster
            cluster_id = _find_or_create_cluster(
                session, detected.embedding, detected.quality_score, face_id
            )

            face = Face(
                id=face_id,
                image_id=image.id,
                bbox_x=detected.bbox[0],
                bbox_y=detected.bbox[1],
                bbox_width=detected.bbox[2],
                bbox_height=detected.bbox[3],
                embedding=detected.embedding,
                cluster_id=cluster_id,
                detection_confidence=detected.confidence,
                quality_score=detected.quality_score,
                thumbnail_path=f"faces/{face_key}",
            )
            session.add(face)

        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"Face detection failed for {image.id}: {e}")


def _find_or_create_cluster(session, embedding: list[float], quality_score: float, face_id: uuid.UUID) -> uuid.UUID:
    """Find matching cluster or create new one. Incremental clustering."""
    from app.models.face import Face, FaceCluster
    import numpy as np

    SIMILARITY_THRESHOLD = 0.68

    clusters = session.query(FaceCluster).filter(FaceCluster.face_count > 0).all()

    best_cluster = None
    best_similarity = 0.0

    emb_array = np.array(embedding)
    emb_norm = emb_array / (np.linalg.norm(emb_array) + 1e-10)

    for cluster in clusters:
        if cluster.representative_face_id:
            rep_face = session.query(Face).filter(Face.id == cluster.representative_face_id).first()
            if rep_face and rep_face.embedding is not None:
                rep_array = np.array(rep_face.embedding)
                rep_norm = rep_array / (np.linalg.norm(rep_array) + 1e-10)
                similarity = float(np.dot(emb_norm, rep_norm))

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_cluster = cluster

    if best_cluster and best_similarity >= SIMILARITY_THRESHOLD:
        best_cluster.face_count += 1
        if quality_score > 0:
            rep_face = session.query(Face).filter(Face.id == best_cluster.representative_face_id).first()
            if rep_face and quality_score > (rep_face.quality_score or 0):
                best_cluster.representative_face_id = face_id
        session.flush()
        return best_cluster.id
    else:
        new_cluster = FaceCluster(
            representative_face_id=face_id,
            face_count=1,
        )
        session.add(new_cluster)
        session.flush()
        return new_cluster.id


def _check_duplicates(session, image):
    """Check for exact and near-duplicate images."""
    from app.models.image import Image as ImageModel
    from app.models.duplicate import DuplicatePair
    from app.ml.hasher import are_near_duplicates

    if not image.file_md5:
        return

    # Check exact duplicates (same MD5)
    exact_dupes = (
        session.query(ImageModel)
        .filter(ImageModel.file_md5 == image.file_md5)
        .filter(ImageModel.id != image.id)
        .all()
    )

    for dupe in exact_dupes:
        existing = (
            session.query(DuplicatePair)
            .filter(
                ((DuplicatePair.image_a_id == image.id) & (DuplicatePair.image_b_id == dupe.id))
                | ((DuplicatePair.image_a_id == dupe.id) & (DuplicatePair.image_b_id == image.id))
            )
            .first()
        )
        if not existing:
            pair = DuplicatePair(
                image_a_id=image.id,
                image_b_id=dupe.id,
                similarity_score=1.0,
                duplicate_type="exact",
                detection_method="md5",
                status="pending",
            )
            session.add(pair)

    # Check near-duplicates (pHash)
    if image.phash:
        all_images = (
            session.query(ImageModel)
            .filter(ImageModel.phash.isnot(None))
            .filter(ImageModel.id != image.id)
            .all()
        )
        for other in all_images:
            if other.phash and are_near_duplicates(image.phash, other.phash):
                existing = (
                    session.query(DuplicatePair)
                    .filter(
                        ((DuplicatePair.image_a_id == image.id) & (DuplicatePair.image_b_id == other.id))
                        | ((DuplicatePair.image_a_id == other.id) & (DuplicatePair.image_b_id == image.id))
                    )
                    .first()
                )
                if not existing:
                    from app.ml.hasher import hamming_distance
                    distance = hamming_distance(image.phash, other.phash)
                    similarity = 1.0 - (distance / 64.0)
                    pair = DuplicatePair(
                        image_a_id=image.id,
                        image_b_id=other.id,
                        similarity_score=similarity,
                        duplicate_type="near",
                        detection_method="phash",
                        status="pending",
                    )
                    session.add(pair)

    session.commit()


@shared_task(name="app.workers.tasks.image_processing.sync_google_photos_task")
def sync_google_photos_task(access_token: str):
    """Sync photos from Google Photos API."""
    import httpx

    session = get_sync_session()
    storage = get_storage()

    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        next_page_token = None
        synced_count = 0

        import asyncio
        loop = asyncio.new_event_loop()

        while True:
            body = {"pageSize": 100}
            if next_page_token:
                body["pageToken"] = next_page_token

            response = httpx.post(
                "https://photoslibrary.googleapis.com/v1/mediaItems:search",
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            data = response.json()

            media_items = data.get("mediaItems", [])
            for item in media_items:
                if item.get("mimeType", "").startswith("image/"):
                    _sync_single_photo(session, storage, loop, item, headers)
                    synced_count += 1

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

        logger.info(f"Google Photos sync completed: {synced_count} photos")
    except Exception as e:
        logger.error(f"Google Photos sync failed: {e}")
    finally:
        session.close()
        loop.close()


def _sync_single_photo(session, storage, loop, item: dict, headers: dict):
    """Sync a single photo from Google Photos."""
    from app.models.image import Image as ImageModel
    import httpx

    source_id = item["id"]

    existing = session.query(ImageModel).filter(ImageModel.source_id == source_id).first()
    if existing:
        return

    base_url = item["baseUrl"]
    download_url = f"{base_url}=d"

    try:
        response = httpx.get(download_url, headers=headers, timeout=30)
        response.raise_for_status()
        image_bytes = response.content

        image_id = uuid.uuid4()
        filename = item.get("filename", f"google_photo_{image_id}.jpg")
        key = f"{image_id}/{filename}"

        loop.run_until_complete(
            storage.upload("photos", key, image_bytes, item.get("mimeType", "image/jpeg"))
        )

        image = ImageModel(
            id=image_id,
            original_filename=filename,
            storage_path=f"photos/{key}",
            file_size=len(image_bytes),
            mime_type=item.get("mimeType", "image/jpeg"),
            source="google_photos",
            source_id=source_id,
            processing_status="pending",
        )
        session.add(image)
        session.commit()

        process_image_pipeline.delay(str(image_id))
    except Exception as e:
        logger.warning(f"Failed to sync photo {source_id}: {e}")
