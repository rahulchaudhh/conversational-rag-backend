# Conversational RAG Backend

A FastAPI-based backend for document-grounded chat and interview booking. It ingests PDF/TXT files, indexes chunks in Pinecone with `BAAI/bge-small-en-v1.5` embeddings, uses Redis for chat memory and rate limiting, and generates responses with Anthropic Claude (including tool-calling for bookings). A bundled static frontend is served from `/`.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)

## Table of Contents
- [Architecture and Capabilities](#architecture-and-capabilities)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Local Development Setup](#local-development-setup)
- [Docker Compose Setup](#docker-compose-setup)
- [API Endpoints](#api-endpoints)
- [Usage Examples](#usage-examples)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Architecture and Capabilities

- **FastAPI API** with routers for documents and chat
- **Document ingestion** for `.pdf` and `.txt` files
- **Chunking strategies**:
  - `recursive` (separator-aware)
  - `fixed` (default 500 chars with 50 overlap)
- **Embeddings** via `sentence-transformers` using `BAAI/bge-small-en-v1.5`
- **Vector storage/retrieval** in Pinecone
- **Redis-backed memory** for multi-turn session history (`chat:<session_id>`)
- **Redis-backed rate limiting** for upload/chat endpoints
- **Anthropic Claude integration** for response generation
- **Claude tool-calling** (`book_interview`) to persist interview bookings
- **SQLAlchemy persistence** for uploaded document metadata and bookings
- **SSE streaming** for token-by-token chat responses
- **Bundled frontend** (`frontend/`) served as static files from `/`

## Project Structure

```text
conversational-rag-backend/
├── app/
│   ├── api/
│   │   ├── chat.py
│   │   └── documents.py
│   ├── core/
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   └── rate_limiter.py
│   ├── db/
│   │   ├── database.py
│   │   └── models.py
│   ├── memory/
│   │   └── redis_memory.py
│   ├── schemas/
│   │   ├── booking.py
│   │   ├── chat.py
│   │   └── document.py
│   ├── services/
│   │   ├── booking_service.py
│   │   ├── chunking_service.py
│   │   ├── document_service.py
│   │   ├── embedding_service.py
│   │   ├── llm_service.py
│   │   └── rag_service.py
│   ├── vector_store/
│   │   └── pinecone.py
│   └── main.py
├── frontend/
│   ├── app.js
│   ├── index.html
│   └── style.css
├── tests/
│   ├── conftest.py
│   ├── test_chat_tools.py
│   ├── test_chunking.py
│   └── test_endpoints.py
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── requirements-dev.txt
```

## Prerequisites

- Python 3.12 recommended
- Redis instance (local or cloud)
- Pinecone API key + existing index
- Anthropic API key
- (Optional) Docker + Docker Compose

## Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `CLAUDE_MODEL` | No | Claude model name (default in config: `claude-haiku-4-5-20251001`) |
| `EMBEDDING_MODEL` | No | Embedding model (default: `BAAI/bge-small-en-v1.5`) |
| `PINECONE_API_KEY` | Yes | Pinecone API key |
| `PINECONE_INDEX` | Yes | Pinecone index name |
| `PINECONE_NAMESPACE` | No | Pinecone namespace |
| `REDIS_URL` | Yes | Redis connection URL |
| `DATABASE_URL` | Yes | SQLAlchemy DB URL (`sqlite:///./rag.db` by default) |
| `RATE_LIMIT_CHAT_RPM` | No | Chat requests/minute |
| `RATE_LIMIT_UPLOAD_RPM` | No | Upload requests/minute |

**Redis URL note**
- Local dev (outside Docker): `redis://localhost:6379/0`
- Docker Compose app->redis networking: `redis://redis:6379/0`

## Local Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open:
- App/frontend: `http://127.0.0.1:8000/`
- OpenAPI docs: `http://127.0.0.1:8000/docs`

## Docker Compose Setup

```bash
docker compose up --build
```

Notes:
- The provided compose file builds/runs the FastAPI app.
- Redis service is present as commented template; if enabling local Redis in compose, also set `REDIS_URL=redis://redis:6379/0` for the app container.
- If using Redis Cloud, keep `REDIS_URL` pointed to your cloud endpoint.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/documents/upload` | Upload + parse + chunk + embed + index document |
| `GET` | `/documents/` | List uploaded documents metadata |
| `POST` | `/chat/` | Chat with RAG + optional SSE streaming + booking tool calls |
| `GET` | `/chat/sessions` | List active Redis chat sessions |
| `GET` | `/chat/bookings` | List stored interview bookings |
| `GET` | `/chat/{session_id}/history` | Get message history for a session |
| `DELETE` | `/chat/{session_id}` | Clear one session’s history |

### Request examples

Upload document:
```bash
curl -X POST "http://127.0.0.1:8000/documents/upload" \
  -F "file=@/absolute/path/to/file.txt" \
  -F "chunking_strategy=recursive"
```

Non-stream chat:
```bash
curl -X POST "http://127.0.0.1:8000/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-session",
    "message": "Summarize the uploaded document.",
    "stream": false
  }'
```

SSE streaming chat:
```bash
curl -N -X POST "http://127.0.0.1:8000/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-session",
    "message": "What does the document say about interview rounds?",
    "stream": true
  }'
```

When `stream=true`, the endpoint returns `text/event-stream` and emits events like token chunks, optional booking events, and a final done event.

## Usage Examples

### 1) Upload a document
```bash
curl -X POST "http://127.0.0.1:8000/documents/upload" \
  -F "file=@/absolute/path/to/candidate_guide.pdf" \
  -F "chunking_strategy=fixed"
```

### 2) Ask a question about uploaded docs
```bash
curl -X POST "http://127.0.0.1:8000/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "candidate-session-1",
    "message": "What requirements are listed for this role?",
    "stream": false
  }'
```

### 3) Book an interview
The booking flow is tool-driven. Provide required details in chat (`name`, `email`, `interview_date`, `interview_time`) and Claude can call `book_interview` internally. Then verify bookings:

```bash
curl -X GET "http://127.0.0.1:8000/chat/bookings"
```

## Testing

Install dev dependencies and run tests:

```bash
pip install -r requirements-dev.txt
pytest -q
```

If your shell environment does not already provide required settings, ensure `.env` exists (for example by copying `.env.example`).

## Troubleshooting

- **Redis connection issues**
  - Verify `REDIS_URL` matches your runtime environment (`localhost` vs `redis` hostname in Docker network).
  - If Redis is unavailable, session history and rate-limiter behavior will degrade/fail.

- **Pinecone upload failures**
  - Confirm `PINECONE_API_KEY`, `PINECONE_INDEX`, and `PINECONE_NAMESPACE`.
  - Ensure your Pinecone index dimension matches embedding output (`BAAI/bge-small-en-v1.5` outputs 384-dim vectors).

- **Unsupported file type errors**
  - Only `.pdf` and `.txt` are accepted by upload endpoints.

- **Empty extraction/chunking errors**
  - Scanned/image-only PDFs may produce no extractable text with `pypdf`.
