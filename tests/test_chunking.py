import pytest
from app.services.chunking_service import ChunkingService


def test_chunking_fixed_and_recursive():
    text = """
    Artificial intelligence is transforming technology.

    Machine learning allows computers to learn from data.

    Large language models can understand and generate text.
    """

    fixed_chunks = ChunkingService.chunk_text(
        text=text,
        strategy="fixed",
        chunk_size=50,
        overlap=10,
    )

    recursive_chunks = ChunkingService.chunk_text(
        text=text,
        strategy="recursive",
        chunk_size=50,
        overlap=10,
    )

    assert len(fixed_chunks) > 0
    assert len(recursive_chunks) > 0
    assert all(isinstance(c, str) for c in fixed_chunks)
    assert all(isinstance(c, str) for c in recursive_chunks)