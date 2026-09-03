from pinecone import Pinecone

from app.core.config import settings


class PineconeService:
    """Service for storing and searching document embeddings in Pinecone."""

    def __init__(self) -> None:
        self.client = Pinecone(
            api_key=settings.pinecone_api_key
        )

        self.index = self.client.Index(
            settings.pinecone_index
        )

    def upsert_chunks(
        self,
        vectors: list[list[float]],
        chunks: list[str],
        document_id: int,
        filename: str,
    ) -> None:
        """Store document chunk embeddings in Pinecone."""

        records = []

        for index, (vector, chunk) in enumerate(
            zip(vectors, chunks)
        ):
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

        self.index.upsert(
            vectors=records,
            namespace=settings.pinecone_namespace,
        )

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
    ) -> list[dict]:
        """Search Pinecone for the most relevant document chunks."""

        result = self.index.query(
            namespace=settings.pinecone_namespace,
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
        )

        matches = []

        for match in result["matches"]:
            metadata = match.get("metadata", {})

            matches.append(
                {
                    "id": match["id"],
                    "score": match["score"],
                    "text": metadata.get("text", ""),
                    "document_id": metadata.get("document_id"),
                    "filename": metadata.get("filename"),
                    "chunk_index": metadata.get("chunk_index"),
                }
            )

        return matches

    def delete_document(self, document_id: int) -> None:
        """Delete all vectors belonging to a document."""

        self.index.delete(
            filter={"document_id": document_id},
            namespace=settings.pinecone_namespace,
        )