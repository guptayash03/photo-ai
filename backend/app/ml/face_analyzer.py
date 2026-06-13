import io
import numpy as np
from PIL import Image
from dataclasses import dataclass


@dataclass
class DetectedFace:
    bbox: tuple[float, float, float, float]  # x, y, w, h (normalized 0-1)
    embedding: list[float]
    confidence: float
    quality_score: float


class FaceAnalyzer:
    _analyzer = None

    @classmethod
    def _get_analyzer(cls):
        if cls._analyzer is None:
            from insightface.app import FaceAnalysis
            cls._analyzer = FaceAnalysis(
                name="buffalo_l",
                providers=["CPUExecutionProvider"],
            )
            cls._analyzer.prepare(ctx_id=0, det_size=(640, 640))
        return cls._analyzer

    def detect_faces(self, image_bytes: bytes) -> list[DetectedFace]:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_array = np.array(img)

        # InsightFace expects BGR
        img_bgr = img_array[:, :, ::-1]

        analyzer = self._get_analyzer()
        faces = analyzer.get(img_bgr)

        height, width = img_array.shape[:2]
        detected = []

        for face in faces:
            bbox = face.bbox  # [x1, y1, x2, y2]
            x1, y1, x2, y2 = bbox

            # Normalize to 0-1
            norm_x = max(0, x1 / width)
            norm_y = max(0, y1 / height)
            norm_w = min(1, (x2 - x1) / width)
            norm_h = min(1, (y2 - y1) / height)

            embedding = face.embedding.tolist() if face.embedding is not None else []
            confidence = float(face.det_score) if hasattr(face, "det_score") else 0.0

            # Quality score based on face size and confidence
            face_area = norm_w * norm_h
            quality = confidence * min(1.0, face_area * 20)

            detected.append(DetectedFace(
                bbox=(norm_x, norm_y, norm_w, norm_h),
                embedding=embedding,
                confidence=confidence,
                quality_score=quality,
            ))

        return detected

    def crop_face(self, image_bytes: bytes, bbox: tuple[float, float, float, float], padding: float = 0.2) -> bytes:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = img.size
        x, y, w, h = bbox

        # Add padding
        pad_x = w * padding
        pad_y = h * padding

        left = max(0, int((x - pad_x) * width))
        top = max(0, int((y - pad_y) * height))
        right = min(width, int((x + w + pad_x) * width))
        bottom = min(height, int((y + h + pad_y) * height))

        face_crop = img.crop((left, top, right, bottom))
        face_crop = face_crop.resize((128, 128), Image.LANCZOS)

        buffer = io.BytesIO()
        face_crop.save(buffer, format="JPEG", quality=85)
        return buffer.getvalue()
