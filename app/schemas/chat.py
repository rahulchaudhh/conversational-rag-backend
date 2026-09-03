from pydantic import BaseModel, Field

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

class ChatResponse(BaseModel):
    session_id: str = Field(
        ..., 
        description="The session identifier."
    )
    reply: str = Field(
        ..., 
        description="The LLM-generated response."
    )