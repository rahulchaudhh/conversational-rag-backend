from fastapi import FastAPI

from app.api.documents import router as documents_router
from app.api.chat import router as chat_router
from app.core.config import settings
from app.db import models
from app.db.database import Base, engine


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.include_router(documents_router)
app.include_router(chat_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "RAG Backend is running!"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}