from abc import ABC, abstractmethod

from app.config import get_settings


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed_image(self, image_bytes: bytes) -> list[float]:
        """Generate embedding vector from image bytes."""
        ...

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding vector from text query."""
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the embedding dimensions."""
        ...


def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    if settings.EMBEDDING_BACKEND == "vertex_ai":
        from app.ml.vertex_embeddings import VertexAIEmbeddings
        return VertexAIEmbeddings()
    else:
        from app.ml.clip_encoder import CLIPLocalEmbeddings
        return CLIPLocalEmbeddings()
