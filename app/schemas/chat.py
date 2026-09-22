from typing import Optional
from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    id: Optional[str] = Field(default=None, description="Vector ID in Pinecone")
    filename: str = Field(default="unknown", description="Source document file name")
    chunk_index: int = Field(default=0, description="Index of the chunk in the document")
    score: float = Field(default=0.0, description="Cosine similarity relevance score")
    text: str = Field(default="", description="Text content of the retrieved chunk")


class ChatRequest(BaseModel):
    session_id: str = Field(
        ..., 
        min_length=1, 
        description="Unique identifier for the chat session to maintain Redis memory."
    )
    message: str = Field(
        ..., 
        min_length=1, 
        description="The user's input question or message."
    )
    stream: bool = Field(
        default=True,
        description="Whether to stream response tokens in real-time."
    )


class ChatResponse(BaseModel):
    session_id: str = Field(
        ..., 
        description="The session identifier."
    )
    reply: str = Field(
        ..., 
        description="The LLM-generated response."
    )
    sources: list[SourceCitation] = Field(
        default_factory=list,
        description="List of document chunk sources retrieved for this turn."
    )