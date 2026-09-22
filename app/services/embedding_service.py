import logging
from typing import Optional
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings with lazy model loading."""

    def __init__(self) -> None:
        self._model: Optional[SentenceTransformer] = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the transformer model once on first use."""
        if self._model is None:
            logger.info(f"Loading embedding model: {settings.embedding_model}...")
            self._model = SentenceTransformer(settings.embedding_model)
        return self._model

    def generate_embeddings(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Generate normalized embeddings for text chunks."""
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
        )

        return embeddings.tolist()