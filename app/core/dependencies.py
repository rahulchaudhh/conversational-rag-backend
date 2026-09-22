"""
Centralized FastAPI dependencies and service life-cycle management.
Ensures services and clients are initialized once, pooled, reused, and cleanly closed.
"""
import logging
from typing import Optional
from fastapi import FastAPI, Depends

from app.core.config import settings
from app.services.embedding_service import EmbeddingService
from app.vector_store.pinecone import PineconeService
from app.memory.redis_memory import RedisMemory
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

# Global singleton references
_embedding_service: Optional[EmbeddingService] = None
_pinecone_service: Optional[PineconeService] = None
_redis_memory: Optional[RedisMemory] = None
_llm_service: Optional[LLMService] = None
_rag_service: Optional[RAGService] = None


def get_embedding_service() -> EmbeddingService:
    """FastAPI dependency for EmbeddingService singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def get_pinecone_service() -> PineconeService:
    """FastAPI dependency for PineconeService singleton."""
    global _pinecone_service
    if _pinecone_service is None:
        _pinecone_service = PineconeService()
    return _pinecone_service


def get_redis_memory() -> RedisMemory:
    """FastAPI dependency for RedisMemory singleton."""
    global _redis_memory
    if _redis_memory is None:
        _redis_memory = RedisMemory()
    return _redis_memory


def get_llm_service() -> LLMService:
    """FastAPI dependency for LLMService singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


def get_rag_service(
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    pinecone_service: PineconeService = Depends(get_pinecone_service),
) -> RAGService:
    """FastAPI dependency for RAGService using injected singletons."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService(
            embedding_service=embedding_service,
            pinecone_service=pinecone_service,
        )
    return _rag_service


async def close_resources() -> None:
    """Clean up open connections on application shutdown."""
    global _redis_memory
    if _redis_memory is not None:
        logger.info("Closing Redis connection pool...")
        _redis_memory.close()
