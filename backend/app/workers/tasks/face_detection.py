import logging
import numpy as np

from celery import shared_task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
sync_engine = create_engine(sync_db_url)
SyncSession = sessionmaker(bind=sync_engine)


@shared_task(name="app.workers.tasks.face_detection.recluster_faces")
def recluster_faces():
    """Periodic re-clustering of faces using DBSCAN for improved accuracy."""
    from app.models.face import Face, FaceCluster
    from sklearn.cluster import DBSCAN

    session = SyncSession()
    try:
        faces = session.query(Face).filter(Face.embedding.isnot(None)).all()

        if len(faces) < 2:
            return

        embeddings = np.array([f.embedding for f in faces])

        # Normalize embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        embeddings_norm = embeddings / norms

        # DBSCAN with cosine distance
        distance_matrix = 1 - np.dot(embeddings_norm, embeddings_norm.T)
        np.fill_diagonal(distance_matrix, 0)

        clustering = DBSCAN(
            eps=0.32,  # 1 - 0.68 threshold
            min_samples=1,
            metric="precomputed",
        ).fit(distance_matrix)

        labels = clustering.labels_
        unique_labels = set(labels) - {-1}

        # Clear old clusters
        session.query(FaceCluster).delete()
        session.flush()

        # Create new clusters
        for label in unique_labels:
            face_indices = [i for i, l in enumerate(labels) if l == label]
            cluster_faces = [faces[i] for i in face_indices]

            # Find best quality face as representative
            best_face = max(cluster_faces, key=lambda f: f.quality_score or 0)

            cluster = FaceCluster(
                representative_face_id=best_face.id,
                face_count=len(cluster_faces),
            )
            session.add(cluster)
            session.flush()

            for face in cluster_faces:
                face.cluster_id = cluster.id

        # Handle noise points (-1 labels) as individual clusters
        noise_indices = [i for i, l in enumerate(labels) if l == -1]
        for idx in noise_indices:
            face = faces[idx]
            cluster = FaceCluster(
                representative_face_id=face.id,
                face_count=1,
            )
            session.add(cluster)
            session.flush()
            face.cluster_id = cluster.id

        session.commit()
        logger.info(f"Re-clustering completed: {len(unique_labels)} clusters from {len(faces)} faces")

    except Exception as e:
        logger.error(f"Face re-clustering failed: {e}")
        session.rollback()
    finally:
        session.close()
