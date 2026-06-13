import io
import numpy as np
from PIL import Image

from app.ml.embedding_provider import EmbeddingProvider


class CLIPLocalEmbeddings(EmbeddingProvider):
    """Fallback CLIP-based embeddings for local development without GCP."""
    _model = None
    _preprocess = None

    @classmethod
    def _load_model(cls):
        if cls._model is None:
            import clip
            import torch
            device = "cpu"
            cls._model, cls._preprocess = clip.load("ViT-B/32", device=device)
            cls._device = device
        return cls._model, cls._preprocess, cls._device

    async def embed_image(self, image_bytes: bytes) -> list[float]:
        import torch
        model, preprocess, device = self._load_model()

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_input = preprocess(image).unsqueeze(0).to(device)

        with torch.no_grad():
            embedding = model.encode_image(image_input)
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)

        # Pad to 1408 dimensions with zeros to match Vertex AI dimension
        emb = embedding.cpu().numpy().flatten().tolist()
        emb.extend([0.0] * (1408 - len(emb)))
        return emb

    async def embed_text(self, text: str) -> list[float]:
        import torch
        import clip
        model, _, device = self._load_model()

        text_input = clip.tokenize([text]).to(device)

        with torch.no_grad():
            embedding = model.encode_text(text_input)
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)

        emb = embedding.cpu().numpy().flatten().tolist()
        emb.extend([0.0] * (1408 - len(emb)))
        return emb

    @property
    def dimensions(self) -> int:
        return 1408
