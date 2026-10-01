# Doc Q&A Portal

A Retrieval-Augmented Generation (RAG) app where you can ingest plain-text documents and ask natural-language questions answered by an LLM grounded in your content.

| | URL |
|---|---|
| **Frontend (Vercel)** | https://rag-aws-nodejs.vercel.app |
| **POST /ingest** | https://o0h2pvizi2.execute-api.us-east-1.amazonaws.com/Prod/ingest |
| **POST /ask** | https://o0h2pvizi2.execute-api.us-east-1.amazonaws.com/Prod/ask |

> The deployed endpoints may be inactive if the AWS stack has been torn down.

---

## Architecture

```
Browser (Next.js / Vercel)
        │
        │  POST /ingest   POST /ask
        ▼
AWS API Gateway (REST, regional)
        │
   ┌────┴────┐
   │         │
IngestFn   AskFn          ← Node.js 24 Lambda (ESM, esbuild)
   │         │
   ├─ OpenAI Embeddings   ← text-embedding-3-small
   │         ├─ OpenAI Embeddings
   ├─ Pinecone upsert     ├─ Pinecone query (cosine, topK)
                          └─ OpenAI LLM (Responses API)
```

**RAG pipeline (implemented from scratch — no LangChain / LlamaIndex):**

```
ingest:  chunk → embed → delete old vectors → upsert to Pinecone
ask:     embed question → query Pinecone → build prompt → call LLM → return answer + sources
```

---

## Project structure

```
├── backend/
│   ├── src/
│   │   ├── lambdas/
│   │   │   ├── ingest/handler.ts   ← POST /ingest Lambda entry point
│   │   │   └── ask/handler.ts      ← POST /ask Lambda entry point
│   │   └── shared/
│   │       ├── chunking.ts         ← TokenChunker (js-tiktoken, sliding window)
│   │       ├── ingestion.ts        ← IngestionService (chunk → embed → upsert)
│   │       ├── rag.ts              ← RagService (embed → query → prompt → answer)
│   │       ├── prompting.ts        ← RAG prompt builder + source deduplication
│   │       ├── openai-services.ts  ← OpenAI embeddings + LLM (Responses API)
│   │       ├── pinecone-store.ts   ← PineconeVectorStore (CRUD + prefix listing)
│   │       ├── config.ts           ← Typed settings from env vars
│   │       ├── domain.ts           ← Core interfaces (ChunkingService, VectorStore…)
│   │       ├── schemas.ts          ← Zod schemas for request/response validation
│   │       ├── http.ts             ← Lambda HTTP helpers (CORS, error responses)
│   │       ├── errors.ts           ← Typed error classes
│   │       └── dependencies.ts     ← Service factory (wires all dependencies)
│   ├── tests/                      ← Vitest unit tests (5 files)
│   ├── template.yaml               ← AWS SAM template (IaC)
│   ├── samconfig.toml              ← SAM deploy defaults
│   └── .env.example                ← Environment variable reference
└── frontend/
    ├── app/
    │   ├── page.tsx                ← Home page with workflow overview
    │   ├── docs/page.tsx           ← Document ingestion page
    │   └── ask/page.tsx            ← Q&A page
    ├── components/                 ← UI components (no external UI library)
    └── lib/
        ├── api.ts                  ← Typed API client with runtime validation
        └── types.ts                ← Shared TypeScript types
```

---

## Local development

### Prerequisites

- Node.js ≥ 24
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- [Docker](https://www.docker.com/) (required by `sam local`)
- OpenAI API key
- Pinecone serverless index (cosine metric, matching `EMBEDDING_DIMENSIONS`)

### Backend

```bash
cd backend
npm install

# Copy and fill in credentials
cp .env.example .env.local   # for sam local invoke
# or edit env.local.json      # for sam local start-api

# Run tests
npm test

# Start local API on http://localhost:3001
sam build
sam local start-api --env-vars env.local.json --port 3001
```

### Frontend

```bash
cd frontend
npm install

# Create env file
cp .env.example .env.local
# Set NEXT_PUBLIC_API_BASE_URL=http://localhost:3001

npm run dev   # http://localhost:3000
```

---

## Environment variables

### Backend (Lambda / `.env.example`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | ✅ | — | OpenAI API key |
| `OPENAI_LLM_MODEL` | ✅ | — | Model for answering (e.g. `gpt-4o-mini`) |
| `OPENAI_EMBEDDING_MODEL` | | `text-embedding-3-small` | Embedding model |
| `EMBEDDING_DIMENSIONS` | | `1536` | Must match Pinecone index dimension |
| `PINECONE_API_KEY` | ✅ | — | Pinecone API key |
| `PINECONE_INDEX` | ✅ | — | Name of the Pinecone index |
| `PINECONE_NAMESPACE` | | `""` | Pinecone namespace (optional) |
| `ALLOWED_ORIGIN` | | `http://localhost:3000` | CORS allowed origin |
| `CHUNK_SIZE` | | `600` | Max tokens per chunk |
| `CHUNK_OVERLAP` | | `100` | Overlapping tokens between chunks |
| `EMBEDDING_BATCH_SIZE` | | `100` | Chunks per OpenAI embedding request |
| `ASK_TOP_K` | | `3` | Number of Pinecone results to retrieve |
| `APP_ENV` | | `development` | Environment label |

### Frontend (`.env.local`)

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | ✅ | Base URL of the deployed or local API |

---

## Deploy

### Backend — AWS SAM

```bash
cd backend

# 1. Build (bundles TypeScript to ESM with esbuild)
sam build

# 2. Deploy (first time, prompts for parameters)
sam deploy --guided

# Subsequent deploys — pass secrets via --parameter-overrides
sam deploy \
  --parameter-overrides \
    OpenAIApiKey=<your-key> \
    PineconeApiKey=<your-key>
```

The SAM template creates:
- Two Lambda functions (`IngestFunction`, `AskFunction`) — Node.js 24, 1024 MB, 90s timeout
- One API Gateway REST API with `POST /ingest` and `POST /ask` routes
- CORS headers scoped to `ALLOWED_ORIGIN`
- IAM permissions (`AWSLambdaBasicExecutionRole`)

The deployed API base URL is printed as `ApiBaseUrl` in the CloudFormation outputs.

> **Note:** API Gateway enforces a 29-second maximum integration timeout. For very large documents or batches, the ingest endpoint may time out. See [Trade-offs](#trade-offs) below.

### Frontend — Vercel

```bash
cd frontend
vercel deploy --prod
```

Set `NEXT_PUBLIC_API_BASE_URL` to the `ApiBaseUrl` value from the SAM deploy output in your Vercel project environment variables.

---

## API reference

### `POST /ingest`

Ingests one or more plain-text documents. Re-ingesting a document with the same `id` replaces it (delete-before-upsert — no duplicates).

**Request**
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

**Response `200`**
```json
{
  "ingestedDocuments": 1,
  "ingestedChunks": 1
}
```

**Error response**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request payload."
  }
}
```

---

### `POST /ask`

Answers a natural-language question using retrieved document chunks.

**Request**
```json
{
  "question": "Can I get a refund on a digital product?"
}
```

**Response `200`**
```json
{
  "answer": "Digital products are not eligible for refunds.",
  "sources": [
    { "docId": "refund-policy", "title": "Refund Policy" }
  ]
}
```

If no relevant documents are found:
```json
{
  "answer": "I couldn't find relevant information in the provided documents.",
  "sources": []
}
```

---

## Chunking strategy

`TokenChunker` uses a **sliding-window token chunker** built on `js-tiktoken` (`cl100k_base` encoding — the same tokenizer used by OpenAI embedding models):

- **Chunk size:** 600 tokens (configurable via `CHUNK_SIZE`)
- **Overlap:** 100 tokens (configurable via `CHUNK_OVERLAP`)
- **Step:** `chunkSize - chunkOverlap` = 500 tokens per advance
- **Vector IDs:** `{docId}#chunk-{index}` (e.g. `refund-policy#chunk-0`)

Token-level chunking keeps chunks within the embedding model's context window and avoids splitting mid-word (unlike character-based splitting). The overlap preserves sentence continuity across chunk boundaries.

---

## Design decisions

**OpenAI Responses API instead of Chat Completions**
The LLM step uses `client.responses.create()` (OpenAI's newer stateless Responses API) rather than `chat.completions.create()`. This requires a model that supports the Responses API.

**Delete-before-upsert for idempotent re-ingestion**
On re-ingest, the service first lists all existing Pinecone vector IDs for the document (using prefix `{docId}#chunk-`), deletes them, then upserts the freshly embedded chunks. New vectors are fully computed before deletion begins, minimizing the window where the document is unavailable.

**Pinecone serverless required**
Prefix-based listing (`listPaginated`) is only available on Pinecone's managed serverless indexes. The `PineconeVectorStore` validates this at startup and rejects other index types early.

**Prompt injection guard**
The RAG prompt instructs the LLM to treat retrieved chunks as untrusted reference data and to never follow instructions found inside them.

**No RAG framework**
The full pipeline (chunk → embed → store → query → prompt → answer) is implemented from scratch using only the Pinecone SDK, the OpenAI SDK, and `js-tiktoken`. No LangChain or LlamaIndex.

---

## Trade-offs

**Synchronous ingest within Lambda**
All chunking, embedding, and Pinecone upserts happen inside the `POST /ingest` Lambda call. The Lambda timeout is configured to 90 seconds, but the effective end-to-end limit is 29 seconds — the API Gateway integration timeout cap for the deployed account/region (a request to raise this limit was rejected by the quota). For large documents or many documents in a single request, the ingest endpoint may time out. The assignment noted SQS + async ingest as a nice-to-have; this is the main production concern.

**Sources deduplication by docId**
If multiple chunks from the same document are retrieved, sources lists only that document once. This keeps the UI clean but loses per-chunk granularity (e.g., which section of a long document matched).

**No streaming**
The LLM answer is returned as a single synchronous response. For longer answers this can feel slow, especially combined with the Lambda cold start.

**Cold starts**
Lambda cold starts add latency on the first request after a period of inactivity. The 1024 MB memory allocation reduces this, but provisioned concurrency would eliminate it for production.

---

## Known limitations

**Pinecone propagation window after re-ingest**
After replacing a document, the new vectors may not be immediately visible to queries. In E2E testing, stale content was sometimes returned for a few seconds after re-ingest completed successfully. Vector ID listing converged quickly (~2 seconds), but query read visibility took up to ~10 seconds in some cases. This is consistent with Pinecone's eventual read consistency, not a backend logic defect.

**Retrieval competition in a shared namespace**
With `ASK_TOP_K=3` and multiple documents stored in the same Pinecone namespace, semantically similar documents from previous sessions can compete for top-K slots. This can affect source attribution when the namespace accumulates diverse test data. Metadata filtering per query or isolated namespaces per session would mitigate this.

**No reranking**
Retrieval is direct dense-vector cosine similarity. No reranker or metadata filter is applied during `/ask`. This is intentional for the prototype scope.

---

## Security notes

- Never commit `env.local.json`, `.env`, or any file containing real API keys. These are gitignored.
- `samconfig.toml` should not contain secret values. Pass `OpenAIApiKey` and `PineconeApiKey` via `--parameter-overrides` at deploy time.
- CloudFormation secret parameters use `NoEcho: true` in `template.yaml`.
- The backend never returns provider payloads, stack traces, or secret values to the client.

---

## If I had more time

- **Async ingest via SQS:** Move chunking + embedding to a background Lambda triggered by SQS, returning a job ID immediately so large batches don't hit the API Gateway timeout.
- **File upload:** Accept PDFs and Word documents via S3 pre-signed URLs + text extraction (Textract or Tika).
- **Smarter chunking:** Split on sentence or paragraph boundaries before applying the token budget, rather than cutting at fixed token counts.
- **Streaming answers:** Use the OpenAI streaming API and stream the response back through API Gateway.
- **Question history:** Persist Q&A sessions to DynamoDB and surface them in the UI.
- **Open Graph metadata:** Add `og:image` and preview card metadata for social sharing.
- **Markdown rendering:** Render LLM responses as Markdown instead of plain text with `white-space: pre-wrap`.

---

## Running tests

```bash
cd backend
npm test
```

Five Vitest test suites / 17 tests cover: chunking logic and configuration validation, the ingest and ask Lambda handlers (with mocked dependencies), OpenAI service batching and error handling, Pinecone store operations, and the end-to-end RAG + ingestion service flows.

Validation sequence used before each deploy:

```bash
npm ci
npm run typecheck
npm test
sam validate
sam validate --lint
sam build
```
