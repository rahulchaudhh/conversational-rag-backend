# Document Ingestion & Conversational RAG Backend

A FastAPI backend implementing two core REST services: the **Document Ingestion API** (PDF/TXT extraction, dual chunking, Pinecone indexing) and the **Conversational RAG API** (custom retrieval, Redis multi-turn memory, native Claude tool-calling, and live streaming SSE), coupled with a **Claude-inspired minimal Chat Interface**.

---

## Features & What I Built

### 1. Minimal Claude-Inspired Web UI (`http://localhost:8000`)
- **Centered Conversational Layout**: Distraction-free ~760px column with equal breathing room and document-grade typography (`15.5px`, `1.7` line-height).
- **Collapsible Workspace Sidebar**:
  - **Indexed Documents (Show PDF/TXT)**: Live overview of all ingested documents with filenames and chunk count badges, plus quick upload.
  - **Chat History**: Multi-turn Redis conversation history with search, session switching, message count pills, and deletion.
  - **Scheduled Interviews Modal**: Quick table view of all booked interviews.
- **Real-Time Token Streaming**: Streams tokens from Claude via Server-Sent Events (SSE).
- **Frictionless Composer Bar**: Rounded floating composer with subtle auto-activating send button on typing.
- **Empty State Quick Actions**: One-click prompt cards ("Book an interview", "Ask about documents", "Ask about our services").

### 2. Document Ingestion API (`POST /documents/upload`)
- **File Parsing**: Handles `.pdf` (using `pypdf`) and `.txt` files.
- **Selectable Chunking Strategies**:
  - `recursive` (default): Recursively splits text using natural separators (`\n\n`, `\n`, `. `, ` `, `""`) to keep coherent paragraphs together.
  - `fixed`: Splits text into fixed character windows with customizable overlap (default 500 chars, 50 overlap).
- **Embeddings**: Generates normalized 384-dimensional dense vectors locally using `sentence-transformers` with `BAAI/bge-small-en-v1.5`.
- **Vector Storage**: Stores vectors and text chunks into **Pinecone** under the configured index and namespace with metadata (`document_id`, `filename`, `chunk_index`, `text`).
- **Database Metadata**: Records document details (`id`, `filename`, `file_type`, `chunking_strategy`, `total_chunks`, `uploaded_at`) into SQL via SQLAlchemy.

### 3. Conversational RAG & Booking API (`POST /chat/`)
- **Custom RAG (No `RetrievalQAChain`)**:
  - Query rewrite & embedding using `bge-small-en-v1.5`.
  - Top-k vector retrieval from Pinecone injected into system context.
- **Multi-Turn Memory with Redis**:
  - Chat history stored in Redis under `chat:<session_id>` as serialized message turns.
  - Prior exchanges loaded on each request to maintain multi-turn context.
- **Native Tool Calling**:
  - Automatically collects required booking details: full name, email, interview date (YYYY-MM-DD), and time (HH:MM).
  - Uses Claude's native `book_interview` tool definition to validate and store bookings into SQL.
- **SSE Streaming Support**: Optional `stream: true` in request body for real-time token streaming.
- **Rate Limiting**: Built-in sliding-window rate limiter powered by Redis (`RATE_LIMIT_CHAT_RPM`, `RATE_LIMIT_UPLOAD_RPM`).

---

![alt text](image-3.png)
![alt text](image-4.png)
![alt text](image-6.png)
![alt text](image-5.png)

---

## Tech Stack

- **Framework**: FastAPI + Uvicorn
- **LLM**: Anthropic Claude (`claude-haiku-4-5-20251001`) via official `anthropic` SDK
- **Embeddings**: `sentence-transformers` (`BAAI/bge-small-en-v1.5`)
- **Vector Database**: Pinecone
- **Memory & Cache**: Redis (Local / Redis Cloud)
- **Database / ORM**: SQLite / PostgreSQL via SQLAlchemy 2.0
- **Frontend**: Vanilla HTML5, CSS3 (Claude-inspired minimal theme), JavaScript (ES6+)
- **Containerization & CI/CD**: Docker, Docker Compose, GitHub Actions

---

## Project Structure

```text
projectrag/
├── app/
│   ├── api/
│   │   ├── chat.py             # Chat endpoint, SSE streaming, booking tool, session history
│   │   └── documents.py        # Upload endpoint (PDF/TXT extraction, chunking, Pinecone indexing)
│   ├── core/
│   │   ├── config.py           # Application settings loaded from .env
│   │   ├── dependencies.py     # FastAPI dependency injections
│   │   └── rate_limiter.py     # Redis-backed rate limiter
│   ├── db/
│   │   ├── database.py         # SQLAlchemy engine and session factory
│   │   └── models.py           # ORM models for Document and Booking
│   ├── memory/
│   │   └── redis_memory.py     # Redis session-based conversation manager
│   ├── schemas/
│   │   ├── booking.py          # Pydantic models for interview booking
│   │   ├── chat.py             # ChatRequest and ChatResponse schemas
│   │   └── document.py         # Document upload response schema
│   ├── services/
│   │   ├── booking_service.py  # Service to persist bookings to database
│   │   ├── chunking_service.py # Fixed-size and recursive chunking implementations
│   │   ├── document_service.py # File extraction for PDF and TXT
│   │   ├── embedding_service.py# SentenceTransformers vector generation
│   │   ├── llm_service.py      # Anthropic Messages API client & tool calling
│   │   └── rag_service.py      # Vector search and prompt context assembly
│   ├── vector_store/
│   │   └── pinecone.py         # Pinecone client for upsert, search, and delete
│   └── main.py                 # FastAPI application entrypoint & static mounting
├── frontend/
│   ├── index.html              # Clean, centered Claude-style chat interface
│   ├── style.css               # Minimalist stylesheet with collapsible sidebar
│   └── app.js                  # SSE streaming, session manager & document listing
├── tests/
│   ├── test_chunking.py        # Chunking strategy unit tests
│   ├── test_chat_tools.py      # Booking tool validation tests
│   └── test_endpoints.py       # API integration tests
├── Dockerfile                  # Container definition
├── docker-compose.yml          # Multi-container orchestration (App + Redis)
├── sample_document.txt         # Sample file for testing ingestion and RAG
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Getting Started

### 1. Clone the repository and navigate into it
```bash
git clone https://github.com/rahulchaudhh/conversational-rag-backend.git
cd conversational-rag-backend
```

### 2. Create and activate a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and configure your credentials:
```bash
cp .env.example .env
```

Required variables:
```env
ANTHROPIC_API_KEY=your_anthropic_api_key
CLAUDE_MODEL=claude-haiku-4-5-20251001

EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX=rag-documents
PINECONE_NAMESPACE=documents

REDIS_URL=redis://localhost:6379/0  # or your Redis Cloud URL
DATABASE_URL=sqlite:///./rag.db     # or PostgreSQL connection string

RATE_LIMIT_CHAT_RPM=30
RATE_LIMIT_UPLOAD_RPM=10
```

### 5. Run the Server
```bash
uvicorn app.main:app --reload
```
Open your browser at **`http://127.0.0.1:8000`** to access the Chat Interface.  
Interactive Swagger API documentation is available at **`http://127.0.0.1:8000/docs`**.

---

## Docker Setup

Run the entire application along with Redis in Docker:

```bash
docker-compose up --build
```
Access the application at `http://localhost:8000`.

---

## API Reference

### 1. Document Ingestion (`POST /documents/upload`)
Upload a PDF or TXT file using either `recursive` or `fixed` chunking:
```bash
curl -X POST "http://127.0.0.1:8000/documents/upload" \
  -F "file=@sample_document.txt" \
  -F "chunking_strategy=recursive"
```

### 2. List Indexed Documents (`GET /documents/`)
```bash
curl -X GET "http://127.0.0.1:8000/documents/"
```

### 3. Conversational RAG & Streaming (`POST /chat/`)
```bash
curl -X POST "http://127.0.0.1:8000/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session1",
    "message": "What services are described in the uploaded document?",
    "stream": true
  }'
```

### 4. Active Sessions (`GET /chat/sessions`)
```bash
curl -X GET "http://127.0.0.1:8000/chat/sessions"
```

### 5. Scheduled Bookings (`GET /chat/bookings`)
```bash
curl -X GET "http://127.0.0.1:8000/chat/bookings"
```
