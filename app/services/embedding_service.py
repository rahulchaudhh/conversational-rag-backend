from sentence_transformers import SentenceTransformer

from app.core.config import settings


class EmbeddingService:
    """Service for generating text embeddings."""

    def __init__(self) -> None:
        self.model = SentenceTransformer(
            settings.embedding_model
        )

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