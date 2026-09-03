from pathlib import Path

from fastapi import UploadFile
from pypdf import PdfReader


class DocumentService:
    """Service for extracting text from PDF and TXT files."""

    @staticmethod
    async def extract_text(file: UploadFile) -> str:
        """Extract text from a PDF or TXT file."""

        filename = file.filename or ""
        extension = Path(filename).suffix.lower()

        if extension == ".txt":
            content = await file.read()
            return content.decode("utf-8")

        if extension == ".pdf":
            reader = PdfReader(file.file)

            text_parts: list[str] = []

            for page in reader.pages:
                page_text = page.extract_text()

                if page_text:
                    text_parts.append(page_text)

            return "\n".join(text_parts)

        raise ValueError(
            "Unsupported file type. Only .pdf and .txt files are allowed."
        )