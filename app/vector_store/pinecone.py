import logging
from typing import Optional
from pinecone import Pinecone
from pinecone.exceptions import PineconeException

from app.core.config import settings

logger = logging.getLogger(__name__)


class PineconeService:
    """Service for storing and searching document embeddings in Pinecone with safe error handling and lazy initialization."""

    def __init__(self) -> None:
        self._client: Optional[Pinecone] = None
        self._index = None

    @property
    def client(self) -> Optional[Pinecone]:
        """Lazy-init Pinecone client so tests/imports without API keys don't crash."""
        if self._client is None:
            api_key = getattr(settings, "pinecone_api_key", None)
            if not api_key or api_key in ("your_pinecone_api_key", ""):
                logger.warning("Pinecone API key is not configured or using dummy placeholder.")
                return None
            try:
                self._client = Pinecone(api_key=api_key)
            except Exception as exc:
                logger.error(f"Failed to initialize Pinecone client: {exc}")
                return None
        return self._client

    @property
    def index(self):
        """Lazy-init Pinecone Index."""
        if self._index is None:
            cli = self.client
            if cli is None:
                return None
            try:
                self._index = cli.Index(settings.pinecone_index)
            except Exception as exc:
                logger.error(f"Failed to connect to Pinecone index '{settings.pinecone_index}': {exc}")
                return None
        return self._index

    def upsert_chunks(
        self,
        vectors: list[list[float]],
        chunks: list[str],
        document_id: int,
        filename: str,
    ) -> None:
        """Store document chunk embeddings in Pinecone."""
        idx = self.index
        if idx is None:
            raise RuntimeError("Pinecone service is unavailable. Please verify PINECONE_API_KEY and PINECONE_INDEX.")

        records = []
        for index, (vector, chunk) in enumerate(zip(vectors, chunks)):
            records.append(
                {
                    "id": f"{document_id}-{index}",
                    "values": vector,
                    "metadata": {
                        "document_id": document_id,
                        "filename": filename,
                        "chunk_index": index,
                        "text": chunk,
                    },
                }
            )

        try:
            idx.upsert(
                vectors=records,
                namespace=settings.pinecone_namespace,
            )
        except PineconeException as exc:
            logger.error(f"Pinecone upsert failed: {exc}")
            raise RuntimeError(f"Pinecone upsert error: {exc}") from exc

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
    ) -> list[dict]:
        """Search Pinecone for the most relevant document chunks."""
        idx = self.index
        if idx is None:
            logger.warning("Pinecone service unavailable for search, returning empty matches.")
            return []

        try:
            result = idx.query(
                namespace=settings.pinecone_namespace,
                vector=query_vector,
                top_k=top_k,
                include_metadata=True,
            )
        except PineconeException as exc:
            logger.error(f"Pinecone search query failed: {exc}")
            return []

        matches = []
        for match in result.get("matches", []):
            metadata = match.get("metadata", {})
            matches.append(
                {
                    "id": match["id"],
                    "score": match.get("score", 0.0),
                    "text": metadata.get("text", ""),
                    "document_id": metadata.get("document_id"),
                    "filename": metadata.get("filename"),
                    "chunk_index": metadata.get("chunk_index"),
                }
            )

        return matches

    def delete_document(self, document_id: int) -> None:
        """Delete all vectors belonging to a document."""
        idx = self.index
        if idx is None:
            logger.warning("Pinecone service unavailable for delete.")
            return

        try:
            idx.delete(
                filter={"document_id": document_id},
                namespace=settings.pinecone_namespace,
            )
        except PineconeException as exc:
            logger.error(f"Pinecone delete failed: {exc}")
            raise RuntimeError(f"Pinecone delete error: {exc}") from exc