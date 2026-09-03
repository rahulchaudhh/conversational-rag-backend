from app.services.chunking_service import ChunkingService


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

print("Fixed chunks:")
print(fixed_chunks)

print("\nRecursive chunks:")
print(recursive_chunks)