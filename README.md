# DocuMind — RAG-Based Document Intelligence Platform

> Upload documents. Ask questions. Get cited answers.

A production-ready, full-stack **Retrieval-Augmented Generation (RAG)** platform built with React, FastAPI, LangChain, ChromaDB, PostgreSQL, and AWS S3 — supporting multi-user workspaces, semantic search, conversational AI, and full source citations.

![Tech Stack](https://img.shields.io/badge/React-18-61DAFB?logo=react) ![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi) ![LangChain](https://img.shields.io/badge/LangChain-0.1-1C3C3C) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql) ![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker) ![AWS S3](https://img.shields.io/badge/AWS-S3-FF9900?logo=amazonaws)

---

## Features

- **PDF Upload & Processing** — Drag-and-drop PDF ingestion with chunking, embedding, and S3 storage
- **Semantic Search** — Vector similarity search over document contents using ChromaDB
- **Chat with Documents** — Conversational Q&A with LangChain RAG chains and GPT-4
- **Enhanced RAG (optional)** — HyDE query expansion and cross-encoder re-ranking (`ms-marco-MiniLM-L-6-v2`) for higher-precision retrieval on demand, via `/api/v1/ml/chat/enhanced`
- **Source Citations** — Every answer includes page-level citations back to source documents
- **ML Document Insights** — Zero-shot classification (BART), NER (BERT), sentiment (DistilBERT), and keyword extraction (TF-IDF + YAKE) run on ingested documents
- **Multi-Tenant Workspaces** — Membership-verified access control with role-based permissions (Owner/Admin/Member/Viewer); documents are visible to workspace members, not just the uploader, and every access path is covered by automated isolation tests
- **Conversation History** — Persistent chat sessions stored in PostgreSQL
- **Responsive UI** — Mobile-first React frontend with dark/light mode

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        React Frontend                        │
│         Upload │ Chat │ Search │ Workspace Dashboard         │
└───────────────────────┬────────────────────────────────────-─┘
                        │ HTTPS / REST + WebSocket
┌───────────────────────▼─────────────────────────────────────┐
│                    FastAPI Backend                           │
│    Auth │ Documents API │ Chat API │ Search API              │
└──────────┬────────────────────────────┬─────────────────────┘
           │                            │
    ┌──────▼──────┐            ┌────────▼────────┐
    │  PostgreSQL  │            │   LangChain     │
    │  Users       │            │   RAG Chain     │
    │  Documents   │            │   + GPT-4       │
    │  Chat Logs   │            └────────┬────────┘
    └─────────────┘                     │
                              ┌─────────▼─────────┐
                              │     ChromaDB       │
                              │  Vector Store      │
                              └───────────────────-┘
                                        │
                              ┌─────────▼─────────┐
                              │      AWS S3        │
                              │  PDF Storage       │
                              └───────────────────-┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, TailwindCSS, Zustand, React Query |
| Backend | FastAPI, Python 3.11, Pydantic v2 |
| AI/LLM | LangChain, OpenAI GPT-4, text-embedding-ada-002 |
| Vector DB | ChromaDB (local) / Pinecone (cloud) |
| Relational DB | PostgreSQL 15 with SQLAlchemy ORM |
| Storage | AWS S3 (Boto3) |
| Auth | JWT (RS256), bcrypt, OAuth2 |
| DevOps | Docker, Docker Compose, Nginx |
| Cloud | AWS EC2 / ECS-ready |

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API Key
- AWS S3 Bucket + IAM credentials

### 1. Clone & Configure

```bash
git clone https://github.com/yourusername/rag-document-platform.git
cd rag-document-platform
cp .env.example .env
# Edit .env with your credentials
```

### 2. Launch with Docker Compose

```bash
docker-compose up --build
```

### 3. Access the App

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| ChromaDB | http://localhost:8001 |

---

## Project Structure

```
documind/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Route handlers (auth, documents, chat, search, ml, workspaces)
│   │   ├── core/            # Config, security, DB
│   │   ├── models/          # SQLAlchemy ORM models (user, document, workspace, chat)
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic (RAG, PDF processing, storage)
│   │   └── ml/               # ML models (classifier, summarizer, NER, sentiment, keywords, reranker) + pipelines
│   ├── tests/                # Pytest suite, incl. workspace isolation tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/            # Route-level pages
│   │   ├── services/         # API client (axios)
│   │   ├── store/            # Zustand state management
│   │   ├── utils/            # Helpers and formatters
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── Dockerfile
│   ├── index.html
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   └── vite.config.js
├── docker/                   # Nginx config
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## API Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login, receive JWT |
| GET | `/api/v1/auth/me` | Get current user |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/documents/upload` | Upload PDF |
| GET | `/api/v1/documents/` | List documents |
| DELETE | `/api/v1/documents/{id}` | Delete document |
| GET | `/api/v1/documents/{id}/status` | Processing status |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat/sessions` | Create chat session |
| GET | `/api/v1/chat/sessions` | List sessions |
| POST | `/api/v1/chat/sessions/{id}/messages` | Send message |
| GET | `/api/v1/chat/sessions/{id}/messages` | Get history |

### Search
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/search/semantic` | Semantic search |

### ML Insights
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/ml/analyze/{document_id}` | Full ML analysis: classify + summarize + NER + sentiment + keywords |
| POST | `/api/v1/ml/chat/enhanced` | RAG chat with optional HyDE query expansion and cross-encoder re-ranking |

### Workspaces
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/workspaces/` | Create a workspace |
| POST | `/api/v1/workspaces/{id}/invite` | Invite a member (Owner/Admin only) |
| GET | `/api/v1/documents/?workspace_id=...` | List documents visible to that workspace |

---

## Skills Demonstrated

- **LLM Engineering** — LangChain RAG chains, prompt templates, context stuffing, HyDE query expansion, cross-encoder re-ranking
- **Vector Databases** — ChromaDB/Pinecone embedding storage and similarity search
- **Applied ML** — Zero-shot classification, NER, sentiment analysis, and keyword extraction served via async FastAPI endpoints
- **Multi-Tenant Access Control** — Workspace membership verification and role-based permissions (Owner/Admin/Member/Viewer), closing an authorization gap where document sharing was schema-scaffolded but not actually enforced
- **Full-Stack Development** — React + FastAPI + PostgreSQL end-to-end
- **Cloud Deployment** — AWS S3, Docker Compose, Nginx reverse proxy
- **Security** — JWT RS256 auth, bcrypt hashing, input validation
- **API Design** — RESTful FastAPI with OpenAPI docs
- **Database Design** — Normalized PostgreSQL schema with SQLAlchemy ORM
- **Automated Testing** — Pytest suite including regression tests that verify cross-workspace data isolation

---

## Testing

```bash
docker-compose exec backend pytest tests/ -v
```

Includes dedicated regression tests (`tests/test_workspace_isolation.py`) proving that:
- a user outside a workspace cannot see or access its documents
- an invited member can view shared documents but cannot delete ones they didn't upload
- uploads cannot be tagged with a workspace the uploader isn't a member of

---

## Environment Variables

See `.env.example` for the full list. Key variables:

```env
OPENAI_API_KEY=sk-...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=documind-pdfs
DATABASE_URL=postgresql://user:pass@db:5432/documind
JWT_SECRET_KEY=your-secret-key
```

---

## License

MIT — free to use in your portfolio.
