from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Document
from app.schemas.document import DocumentUploadResponse
from app.services.chunking_service import ChunkingService
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.vector_store.pinecone import PineconeService
from app.core.config import settings
from app.core.rate_limiter import RateLimiter
from app.core.dependencies import get_embedding_service, get_pinecone_service


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

upload_limiter = RateLimiter(times=settings.rate_limit_upload_rpm, seconds=60, key_prefix="rl_upload")


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    dependencies=[Depends(upload_limiter)],
)
async def upload_document(
    file: UploadFile = File(...),
    chunking_strategy: Literal["fixed", "recursive"] = Form("recursive"),
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    pinecone_service: PineconeService = Depends(get_pinecone_service),
) -> DocumentUploadResponse:

    filename = file.filename or ""

    if not filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are supported.",
        )

    try:
        # 1. Extract text
        text = await DocumentService.extract_text(file)

        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="The uploaded document contains no readable text.",
            )

        # 2. Chunk text
        chunks = ChunkingService.chunk_text(
            text=text,
            strategy=chunking_strategy,
        )

        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="Could not create document chunks.",
            )

        # 3. Save document metadata
        document = Document(
            filename=filename,
            file_type=filename.rsplit(".", 1)[-1].lower(),
            chunking_strategy=chunking_strategy,
            total_chunks=len(chunks),
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        # 4. Generate embeddings (using injected singleton service)
        embeddings = embedding_service.generate_embeddings(chunks)

        # 5. Store embeddings in Pinecone (using injected singleton service)
        pinecone_service.upsert_chunks(
            vectors=embeddings,
            chunks=chunks,
            document_id=document.id,
            filename=filename,
        )

        return DocumentUploadResponse(
            document_id=document.id,
            filename=filename,
            chunking_strategy=chunking_strategy,
            total_chunks=len(chunks),
            message="Document uploaded and indexed successfully.",
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


@router.get("/")
def list_documents(db: Session = Depends(get_db)):
    """Retrieve all uploaded and indexed documents."""
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "file_type": doc.file_type,
            "chunking_strategy": doc.chunking_strategy,
            "total_chunks": doc.total_chunks,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        }
        for doc in docs
    ]