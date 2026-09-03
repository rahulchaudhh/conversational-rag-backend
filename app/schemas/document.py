from typing import Literal

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    document_id: int
    filename: str
    chunking_strategy: Literal["fixed", "recursive"]
    total_chunks: int
    message: str