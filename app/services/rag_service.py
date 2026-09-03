from typing import Any

from app.services.embedding_service import EmbeddingService
from app.vector_store.pinecone import PineconeService


class RAGService:
    """Service for retrieving relevant context from the knowledge base."""

    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()
        self.pinecone_service = PineconeService()

    def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Retrieve the most relevant document chunks for a user query.

        Args:
            query: User's question.
            top_k: Maximum number of chunks to retrieve.

        Returns:
            Relevant document chunks returned by Pinecone.
        """
        if not query.strip():
            return []

        query_embedding = self.embedding_service.generate_embeddings(
            [query],
        )[0]

        return self.pinecone_service.search(
            query_vector=query_embedding,
            top_k=top_k,
        )

    @staticmethod
    def build_context(
        matches: list[dict[str, Any]],
    ) -> str:
        """
        Convert retrieved Pinecone matches into LLM-ready context.
        """
        context_parts: list[str] = []

        for index, match in enumerate(matches, start=1):
            text = str(match.get("text", "")).strip()

            if not text:
                continue

            filename = str(match.get("filename", "unknown"))

            context_parts.append(
                f"[Source {index}: {filename}]\n{text}"
            )

        return "\n\n".join(context_parts)