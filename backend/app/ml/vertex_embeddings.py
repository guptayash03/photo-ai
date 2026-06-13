import base64
import io

from google.cloud import aiplatform
from vertexai.vision_models import MultiModalEmbeddingModel, Image as VertexImage

from app.config import get_settings
from app.ml.embedding_provider import EmbeddingProvider


class VertexAIEmbeddings(EmbeddingProvider):
    _model = None

    def __init__(self):
        settings = get_settings()
        if settings.GCP_PROJECT_ID:
            aiplatform.init(
                project=settings.GCP_PROJECT_ID,
                location=settings.GCP_REGION,
            )

    @classmethod
    def _get_model(cls):
        if cls._model is None:
            cls._model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding@001")
        return cls._model

    async def embed_image(self, image_bytes: bytes) -> list[float]:
        model = self._get_model()
        image = VertexImage(image_bytes=image_bytes)
        embeddings = model.get_embeddings(image=image, dimension=1408)
        return embeddings.image_embedding

    async def embed_text(self, text: str) -> list[float]:
        model = self._get_model()
        embeddings = model.get_embeddings(contextual_text=text, dimension=1408)
        return embeddings.text_embedding

    @property
    def dimensions(self) -> int:
        return 1408
