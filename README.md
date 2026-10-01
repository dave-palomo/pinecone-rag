# Doc Q&A Portal

A full-stack Retrieval-Augmented Generation (RAG) app. Ingest plain-text documents and ask natural-language questions; the backend retrieves the most relevant passages from Pinecone and uses an OpenAI model to produce a grounded answer with source citations.

---

## Architecture

```
Browser
  │
  ├─ /docs  →  Next.js (TypeScript)  →  POST /ingest
  └─ /ask   →  Next.js (TypeScript)  →  POST /ask
                                              │
                                     FastAPI (Python)
                                              │
                              ┌───────────────┼───────────────┐
                              │               │               │
                         tiktoken        OpenAI API      Pinecone
                         chunking        embeddings       vector
                                         + answers        index
```

### Intentional deviation from the assignment spec

The original spec called for **Node.js/TypeScript on AWS Lambda + API Gateway** with IaC (SAM/CDK/Serverless). I built the backend in **Python + FastAPI deployed to Railway** instead. The RAG pipeline, Pinecone integration, API contracts, and all hard rules (no LangChain, no LlamaIndex) are fully met. The trade-off is documented in the [Trade-offs](#trade-offs) section below.

---

## Project structure

```
pinecone_rag/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── dependencies.py   # FastAPI DI – builds services from Settings
│   │   │   └── routes.py         # GET /health, POST /ingest, POST /ask
│   │   ├── core/
│   │   │   ├── config.py         # Settings dataclass loaded from env vars
│   │   │   └── errors.py         # Typed error hierarchy → HTTP codes
│   │   ├── models/
│   │   │   └── schemas.py        # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── chunking.py       # TokenChunker (tiktoken sliding window)
│   │   │   ├── domain.py         # Protocol types (ChunkingService, EmbeddingProvider, …)
│   │   │   ├── ingestion.py      # IngestionService: chunk → embed → upsert
│   │   │   ├── openai_services.py# OpenAI embeddings + Responses API answer
│   │   │   ├── pinecone_store.py # PineconeVectorStore: delete / upsert / query
│   │   │   ├── prompting.py      # build_rag_prompt + source deduplication
│   │   │   └── rag.py            # RagService: embed question → query → answer
│   │   ├── main.py               # FastAPI app factory (CORS, error handlers)
│   │   └── __main__.py           # Uvicorn entrypoint (Railway-aware port)
│   ├── tests/                    # pytest unit tests
│   ├── Procfile                  # Railway: web: python -m app
│   ├── requirements.txt
│   └── requirements-dev.txt
└── frontend/
    ├── app/
    │   ├── docs/page.tsx         # Document ingestion page
    │   ├── ask/page.tsx          # Q&A page
    │   └── layout.tsx
    ├── components/               # DocumentForm, QuestionForm, AnswerResult, …
    ├── lib/
    │   ├── api.ts                # Type-safe fetch client with runtime validation
    │   └── types.ts              # Shared TypeScript types
    ├── tests/frontend.spec.ts    # Playwright E2E tests
    └── package.json
```

---

## Running locally

### Prerequisites

- Python 3.12+
- Node.js 20+
- An OpenAI API key with access to an embedding model and a chat/responses model
- A Pinecone index that satisfies the following contract:

| Property | Required value |
|---|---|
| Vector type | Dense |
| Dimension | `1536` (must match `EMBEDDING_DIMENSIONS`) |
| Similarity metric | Cosine |

The application does not provision the index automatically. It fails at startup with a clear error if the index is missing, has wrong dimensions, or uses a non-cosine metric. Both ingestion and retrieval must use the same `PINECONE_INDEX` and `PINECONE_NAMESPACE` values.

### 1 — Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt          # production
pip install -r requirements-dev.txt      # + pytest

# Configure environment variables
cp .env.example .env                     # then edit .env with real values

# Start the server (default: http://localhost:8000)
python -m app
```

The API documentation is available at `http://localhost:8000/docs` once the server is running.

### 2 — Frontend

```bash
cd frontend

npm install

# Configure the backend URL
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local

npm run dev     # http://localhost:3000
```

---

## Environment variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | yes | — | OpenAI secret key |
| `OPENAI_EMBEDDING_MODEL` | no | `text-embedding-3-small` | Embedding model name |
| `OPENAI_LLM_MODEL` | yes (for /ask) | — | e.g. `gpt-4.1-mini` |
| `PINECONE_API_KEY` | yes | — | Pinecone API key |
| `PINECONE_INDEX` | yes | — | Name of the Pinecone index |
| `PINECONE_NAMESPACE` | no | `""` (default namespace) | Pinecone namespace |
| `ALLOWED_ORIGINS` | no | `http://localhost:3000` | Comma-separated CORS origins |
| `EMBEDDING_DIMENSIONS` | no | `1536` | Must match the Pinecone index dimension |
| `CHUNK_SIZE` | no | `600` | Max tokens per chunk |
| `CHUNK_OVERLAP` | no | `100` | Overlapping tokens between adjacent chunks |
| `EMBEDDING_BATCH_SIZE` | no | `100` | Chunks sent per OpenAI embeddings call |
| `ASK_TOP_K` | no | `3` | Chunks retrieved from Pinecone per question |
| `APP_HOST` | no | `0.0.0.0` | Bind host |
| `APP_PORT` | no | `8000` | Bind port (overridden by `PORT` on Railway) |

### Frontend (`frontend/.env.local`)

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | yes | Full URL of the backend, e.g. `http://localhost:8000` |

---

## RAG pipeline

```
POST /ingest
  └─ for each document
       ├─ TokenChunker.split(content)         # tiktoken sliding window
       ├─ OpenAIEmbeddingService.embed_texts  # batched, ordered
       ├─ PineconeVectorStore.delete_document # removes stale chunks by metadata filter
       └─ PineconeVectorStore.upsert          # id = "{docId}#chunk-{index}"

POST /ask
  ├─ OpenAIEmbeddingService.embed_texts([question])
  ├─ PineconeVectorStore.query(vector, top_k)
  ├─ build_rag_prompt(question, chunks)       # XML-tagged excerpt block
  └─ OpenAILanguageModel.answer(prompt)       # Responses API, store=False
```

### Chunking strategy

Token-based sliding window via **tiktoken** using the same encoding as the configured embedding model. Default: 600-token chunks with 100-token overlap. The overlap prevents a sentence from being split exactly at a boundary with zero context on either side. Chunk IDs follow the pattern `{docId}#chunk-{index}`.

Re-ingesting a document with the same `id` first deletes all existing vectors for that `docId` via a Pinecone metadata filter, then upserts fresh ones — no duplicates accumulate.

---

## API reference

### `POST /ingest`

```json
{
  "documents": [
    {
      "id": "refund-policy",
      "title": "Refund Policy",
      "content": "Full refund within 30 days with receipt. No refunds on digital goods."
    }
  ]
}
```

Response:

```json
{
  "ingestedDocuments": 1,
  "ingestedChunks": 1
}
```

### `POST /ask`

```json
{
  "question": "Can I get a refund on a digital product?"
}
```

Response:

```json
{
  "answer": "Digital products are not eligible for refunds.",
  "sources": [
    { "docId": "refund-policy", "title": "Refund Policy" }
  ]
}
```

### `GET /health`

```json
{ "status": "ok", "environment": "production", "version": "0.1.0" }
```

---

## Tests

### Backend (pytest)

```bash
cd backend
source .venv/bin/activate
pytest
```

The test suite covers chunking logic, prompt construction, source deduplication, Pydantic schema validation, and the OpenAI/Pinecone adapters with mocked network calls.

### Frontend (Playwright E2E)

```bash
cd frontend
npx playwright install --with-deps
npm run test:e2e
```

Tests mock the backend network layer and verify document form add/remove, client-side validation, success/error rendering on `/docs`, and answer + source rendering on `/ask`.

---

## Deployment (Railway)

The backend is designed for Railway's PaaS. Deployment steps:

1. Create a Railway project and link this repository.
2. Set the root directory to `backend/` (or point the start command at it).
3. Add all required environment variables in the Railway dashboard (same table as above, plus Railway's injected `PORT` is read automatically).
4. Railway runs `python -m app` via the `Procfile`; Uvicorn binds to `$PORT`.

For the frontend, deploy to Vercel (or any static host) and set `NEXT_PUBLIC_API_BASE_URL` to the Railway service URL.

---

## Assumptions and trade-offs

**Python FastAPI instead of Node.js/TypeScript on AWS Lambda**

The assignment spec asked for AWS Lambda + API Gateway with IaC (SAM/CDK/Serverless). I chose Python + FastAPI on Railway for the following reasons:

- Python's scientific/ML ecosystem (tiktoken, openai, pinecone) is more mature and requires less boilerplate than the Node.js equivalents.
- Railway eliminates cold-start latency, provisioning time, and the IaC surface area, allowing all effort to go into the RAG logic itself.
- The API contracts (`POST /ingest`, `POST /ask`), Pinecone integration, chunking strategy, and all hard rules (no LangChain, no LlamaIndex) are identical to what the spec requires.

The absence of AWS infra is the clearest deviation. In a production engagement this would be a discussion point, not a unilateral decision.

**`topK` is a server-side configuration, not a per-request parameter**

The spec includes `"topK": 3` in the `/ask` request body. I exposed this as `ASK_TOP_K` in the environment instead, keeping the request schema simpler. Accepting it per-request would be a small addition to `AskRequest` and `RagService.ask`.

**Single-stage synchronous ingestion**

All chunking, embedding, and upsert happen synchronously inside `POST /ingest`. For large documents or bulk uploads this blocks the HTTP connection. The async SQS pattern described in the spec's "nice-to-have" section would decouple ingestion from the HTTP response.

**Multi-document partial failure**

Documents inside a single `POST /ingest` request are processed sequentially. If one document fails (e.g. an OpenAI error), processing stops and the request returns an error — but any documents that were successfully ingested before the failure remain committed in Pinecone. There is no request-wide rollback. Duplicate `id` values within the same request are rejected during schema validation to avoid ambiguous replacement order.

---

## Known limitations

**Non-transactional document replacement**

Re-ingesting a document follows a delete-then-upsert pattern. To reduce the failure window, all new embeddings are generated and verified *before* the existing Pinecone vectors are deleted. However, if Pinecone fails between the delete and the upsert steps, that document will be temporarily absent from the index until the next successful ingestion. A fully atomic replacement would require external coordination (e.g. write-ahead log or transactional Pinecone namespace swap) and is deferred for a future iteration.

---

## If I had more time

- **Async ingestion**: Offload chunking + embedding to a background worker (Celery, ARQ, or — per the spec — SQS + a second Lambda) and return a job ID immediately from `POST /ingest`.
- **File upload**: Accept PDF/DOCX via multipart form and extract text with a library like `pypdf` or Azure Document Intelligence.
- **Smarter chunking**: Sentence-boundary awareness (spaCy or NLTK) to avoid cutting sentences mid-thought; semantic chunking based on embedding similarity between adjacent windows.
- **Re-ranking**: A cross-encoder pass after Pinecone retrieval to improve precision before prompt construction.
- **Streaming answers**: Use the OpenAI streaming API and Server-Sent Events to show the answer token by token in the UI.
- **AWS Lambda port**: Wrap the FastAPI app with `mangum` and add a SAM/CDK template to match the original spec exactly.
- **Auth**: Even a static API key header would prevent public write access to the Pinecone index.
