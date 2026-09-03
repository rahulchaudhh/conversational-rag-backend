import re


class ChunkingService:
    """Service for splitting document text into chunks."""

    @staticmethod
    def fixed_size_chunking(
        text: str,
        chunk_size: int = 500,
        overlap: int = 50,
    ) -> list[str]:
        """Split text into fixed-size character chunks."""

        chunks: list[str] = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            start += chunk_size - overlap

        return chunks

    @staticmethod
    def recursive_chunking(
        text: str,
        chunk_size: int = 500,
        overlap: int = 50,
    ) -> list[str]:
        """Split text recursively using natural separators."""

        separators = ["\n\n", "\n", ". ", " ", ""]

        chunks = [text]

        for separator in separators:
            new_chunks: list[str] = []

            for chunk in chunks:
                if len(chunk) <= chunk_size:
                    new_chunks.append(chunk)
                    continue

                if separator == "":
                    new_chunks.extend(
                        [
                            chunk[i:i + chunk_size]
                            for i in range(0, len(chunk), chunk_size)
                        ]
                    )
                else:
                    parts = chunk.split(separator)
                    current_chunk = ""

                    for part in parts:
                        candidate = (
                            f"{current_chunk}{separator}{part}"
                            if current_chunk
                            else part
                        )

                        if len(candidate) <= chunk_size:
                            current_chunk = candidate
                        else:
                            if current_chunk:
                                new_chunks.append(current_chunk.strip())

                            current_chunk = part

                    if current_chunk:
                        new_chunks.append(current_chunk.strip())

            chunks = new_chunks

        return [
            chunk
            for chunk in chunks
            if chunk.strip()
        ]

    @staticmethod
    def chunk_text(
        text: str,
        strategy: str,
        chunk_size: int = 500,
        overlap: int = 50,
    ) -> list[str]:
        """Select and apply a chunking strategy."""

        if strategy == "fixed":
            return ChunkingService.fixed_size_chunking(
                text=text,
                chunk_size=chunk_size,
                overlap=overlap,
            )

        if strategy == "recursive":
            return ChunkingService.recursive_chunking(
                text=text,
                chunk_size=chunk_size,
                overlap=overlap,
            )

        raise ValueError(
            "Invalid chunking strategy. Use 'fixed' or 'recursive'."
        )