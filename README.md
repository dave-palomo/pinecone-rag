# Doc Q&A Portal — Python AWS Lambda prototype

## Live deployment

| | URL |
|---|---|
| Frontend (Vercel) | <https://pinecone-rag-frontend-4hjc.vercel.app> |
| API Gateway (AWS) | `https://jn28szhiv8.execute-api.us-east-1.amazonaws.com/Prod` |
| POST /ingest | `https://jn28szhiv8.execute-api.us-east-1.amazonaws.com/Prod/ingest` |
| POST /ask | `https://jn28szhiv8.execute-api.us-east-1.amazonaws.com/Prod/ask` |

---

This repository is a full-stack RAG application with a **Next.js frontend** and a
**serverless Python backend** deployed on AWS (API Gateway + Lambda + SAM).

- `POST /ingest` chunks plain-text documents, creates OpenAI embeddings, and replaces
  the corresponding vectors in Pinecone.
- `POST /ask` embeds a natural-language question, retrieves relevant Pinecone chunks,
  and asks an OpenAI model to answer using only that context.

The backend is declared in `backend/template.yaml` with AWS SAM and is intentionally
free of FastAPI, Mangum, LangChain, and LlamaIndex.

> **Note — language deviation.** The original take-home assignment specified
> Node.js + TypeScript on Lambda. This branch implements the same AWS architecture in
> Python 3.12 to validate the full request path and deployment model before porting to
> the final TypeScript version. The external API contract (routes, request/response
> shapes, CORS, error envelope) is identical.

---

## Repository structure

```text
.
├── backend/
│   ├── lambdas/
│   │   ├── ingest/handler.py   # POST /ingest Lambda entry point
│   │   └── ask/handler.py      # POST /ask Lambda entry point
│   ├── shared/                 # Provider-neutral business logic
│   │   ├── chunking.py
│   │   ├── ingestion.py
│   │   ├── rag.py
│   │   ├── prompting.py
│   │   ├── openai_services.py
│   │   ├── pinecone_store.py
│   │   ├── schemas.py
│   │   ├── domain.py
│   │   ├── dependencies.py
│   │   ├── config.py
│   │   ├── errors.py
│   │   └── http.py
│   ├── tests/
│   ├── events/                 # SAM local test payloads
│   ├── template.yaml           # SAM IaC
│   ├── Makefile                # Custom SAM build steps
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── .env.example            # Reference for local Python execution
│   └── env.local.example.json  # Reference for SAM-local execution
└── frontend/                   # Next.js + TypeScript client
```

---

## Configuration

### Backend

All Lambda configuration comes from environment variables.

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | — | OpenAI secret key |
| `OPENAI_LLM_MODEL` | Yes | — | Chat completion model (e.g. `gpt-4o-mini`) |
| `OPENAI_EMBEDDING_MODEL` | No | `text-embedding-3-small` | Embedding model |
| `EMBEDDING_DIMENSIONS` | No | `1536` | Must match the Pinecone index dimension |
| `EMBEDDING_BATCH_SIZE` | No | `100` | Chunks per OpenAI embedding request |
| `PINECONE_API_KEY` | Yes | — | Pinecone secret key |
| `PINECONE_INDEX` | Yes | — | Name of an existing Pinecone index |
| `PINECONE_NAMESPACE` | No | `""` | Pinecone namespace (empty = default) |
| `CHUNK_SIZE` | No | `600` | Maximum tokens per chunk |
| `CHUNK_OVERLAP` | No | `100` | Overlap tokens between consecutive chunks |
| `ASK_TOP_K` | No | `3` | Number of chunks retrieved per question |
| `ALLOWED_ORIGIN` | No | `http://localhost:3000` | CORS allowed frontend origin |
| `APP_ENV` | No | `development` | Environment tag |

The Pinecone index must already exist as a **dense cosine-similarity index** whose
dimension matches `EMBEDDING_DIMENSIONS`. Ingestion and retrieval must use the same
`PINECONE_NAMESPACE`.

For local **Python** execution copy `backend/.env.example` to `backend/.env` and fill
in the values.

For **SAM-local** execution copy `backend/env.local.example.json` to
`backend/env.local.json` and fill in the values. This file is gitignored and must
never be committed.

### Frontend

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Yes | Base URL of the backend (no trailing slash) |

Copy `frontend/.env.example` to `frontend/.env.local` and set the variable.

---

## Chunking strategy

Content is tokenized with `tiktoken` (`cl100k_base` encoding) and split into
overlapping windows:

```
step = CHUNK_SIZE − CHUNK_OVERLAP  →  500 tokens by default
```

Each chunk receives a deterministic Pinecone vector ID:

```
{docId}#chunk-{index}   →   refund-policy#chunk-0, refund-policy#chunk-1, …
```

This means re-ingesting the same `docId` reliably identifies and replaces all
previous vectors for that document.

---

## Backend — local install and tests

Docker Desktop is **not** required for running unit tests.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest
```

---

## Backend — SAM local execution

Docker Desktop must be running because `tiktoken` contains platform-specific
components and the deployment package must target Amazon Linux 2023.

```powershell
cd backend
sam validate
sam validate --lint
sam build --use-container
sam local invoke IngestFunction -e events/ingest.json --env-vars env.local.json
sam local invoke AskFunction    -e events/ask.json    --env-vars env.local.json
sam local start-api --env-vars env.local.json --port 3001
```

Local routes (note port **3001** to avoid colliding with the Next.js dev server on 3000):

- `POST http://127.0.0.1:3001/ingest`
- `POST http://127.0.0.1:3001/ask`

Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:3001` in `frontend/.env.local` when
running both locally.

---

## Frontend — local setup

```bash
cd frontend
npm install
# edit frontend/.env.local and set NEXT_PUBLIC_API_BASE_URL
npm run dev
```

Open <http://localhost:3000>.

- `/docs` — add documents and call `POST /ingest`
- `/` — ask questions and call `POST /ask`

---

## Deploy

```powershell
# First deploy (interactive — enter stack name, region, and parameters)
cd backend
sam build --use-container
sam deploy --guided

# Subsequent deploys
sam deploy
```

The guided flow prompts for all CloudFormation parameters (API keys, model names,
Pinecone index). The resulting `ApiBaseUrl` stack output is the base URL you need.

Set that value as `NEXT_PUBLIC_API_BASE_URL` in your frontend environment before
deploying or building the frontend (e.g. on Vercel: Root Directory = `frontend`,
Environment Variable = `NEXT_PUBLIC_API_BASE_URL=https://<api-id>.execute-api.<region>.amazonaws.com/Prod`).

---

## Example requests

### POST /ingest

```bash
curl -X POST http://127.0.0.1:3001/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "id": "refund-policy",
        "title": "Refund Policy",
        "content": "Full refund within 30 days with receipt. No refunds on digital goods."
      }
    ]
  }'
```

Expected response:

```json
{
  "ingestedDocuments": 1,
  "ingestedChunks": 1
}
```

### POST /ask

```bash
curl -X POST http://127.0.0.1:3001/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Can I get a refund on a digital product?"}'
```

Expected response:

```json
{
  "answer": "Digital products are not eligible for refunds.",
  "sources": [
    { "docId": "refund-policy", "title": "Refund Policy" }
  ]
}
```

---

## Assumptions and trade-offs

| Area | Decision | Reason |
|---|---|---|
| Language | Python 3.12 instead of Node.js/TypeScript | Validates AWS architecture before the final TS port; the external contract is unchanged |
| HTTP framework | Native Lambda handlers, no FastAPI/Mangum | Only two routes; the extra ASGI adapter layer adds complexity without value |
| RAG frameworks | None (LangChain, LlamaIndex excluded) | The chunking → embed → store → query → prompt → LLM flow is straightforward enough to implement directly |
| Re-ingestion | Delete-then-upsert per document | Ensures stale chunks from a shorter revised document are fully removed |
| Sync ingest | Synchronous inside the Lambda | Adequate for small plain-text documents within the 29-second API Gateway limit |
| Async ingest (S3 + SQS) | Not implemented | Out of scope for this prototype; described in "If I had more time" |
| Authentication | None | Not required by the assignment |
| Pinecone index | Must be pre-created | Automatic index creation adds deployment coupling without benefit for a prototype |

### Atomicity trade-off

Re-ingestion embeds all new chunks **before** deleting old vectors, which minimises
the failure window. However, Pinecone does not provide a transaction across the
subsequent delete and upsert. A failure in that window can temporarily remove or
partially replace a document. This is accepted for the synchronous prototype.

---

## If I had more time, I would…

- **Async ingest via S3 + SQS.** The `/ingest` Lambda would write the document to S3
  and publish a message to SQS. A second processor Lambda subscribed to the queue
  would handle chunking, embedding, and Pinecone upserts — removing the 29-second
  synchronous constraint for large documents.

- **Node.js / TypeScript port.** Translate the validated architecture into the final
  TypeScript Lambda version required by the original assignment.

- **Pin production dependency versions.** Currently `requirements.txt` uses unpinned
  ranges. Pinning resolved versions makes deployments reproducible.

- **Secrets Manager.** Move OpenAI and Pinecone keys from CloudFormation parameters /
  Lambda environment variables into AWS Secrets Manager for rotation support and audit
  trail.

- **Smarter chunking.** Sentence-boundary-aware chunking (instead of pure token
  windows) and a reranker step would improve retrieval quality.

- **Streaming answers.** Return the LLM response as a stream so users see tokens
  appear progressively instead of waiting for the full answer.

- **File upload + text extraction.** Accept PDF/DOCX uploads and extract plain text
  with Textract or similar before chunking.

- **Unit test coverage for all edge cases.** Current tests cover the happy path and
  major error branches; property-based testing of the chunker and adversarial prompt
  injection resistance would add confidence.
