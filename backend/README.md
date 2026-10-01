# RAG backend: AWS SAM + TypeScript

This service implements the Doc Q&A Portal backend with two synchronous REST endpoints:

```text
POST /ingest  -> chunks documents -> OpenAI embeddings -> Pinecone
POST /ask     -> embeds question -> Pinecone search -> OpenAI grounded answer
```

It is deliberately a prototype. It does not include authentication, asynchronous ingestion, PDF extraction, or a database. Re-ingesting a document replaces vectors with the deterministic `documentId:chunkIndex` prefix. Because the replacement is delete-then-upsert, a provider failure during upsert can leave a document partially indexed; production ingestion should evolve to an asynchronous/versioned workflow.

## Prerequisites

- Node.js 24
- Docker Desktop running (for `sam local`)
- AWS SAM CLI and an AWS profile (for deployment)
- OpenAI and Pinecone API keys
- A Pinecone **managed/serverless** dense index with `1536` dimensions and `cosine` metric. The service checks this before use.

## Configuration and secrets

For local SAM execution, copy the template and fill in your values:

```powershell
Copy-Item env.local.example.json env.local.json
```

`env.local.json` is ignored by Git and is the file SAM reads with `--env-vars env.local.json`. Do not commit it or paste its contents into logs/chat.

`.env.example` lists the same variables in conventional `.env` format for reference. Lambdas do not load `.env` files themselves; SAM local takes `env.local.json` and AWS deployment uses CloudFormation parameters. The two API-key parameters are configured with `NoEcho`.

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | OpenAI API key |
| `PINECONE_API_KEY` | Pinecone API key |
| `PINECONE_INDEX` | Existing Pinecone index name |
| `PINECONE_NAMESPACE` | Namespace (blank is valid) |
| `OPENAI_EMBEDDING_MODEL` | Default: `text-embedding-3-small` |
| `EMBEDDING_DIMENSIONS` | Default: `1536` |
| `OPENAI_LLM_MODEL` | Default: `gpt-5-mini` |
| `CHUNK_SIZE` | Default: `600` |
| `CHUNK_OVERLAP` | Default: `100` |
| `EMBEDDING_BATCH_SIZE` | Default: `100` |
| `ASK_TOP_K` | Default: `3` |
| `ALLOWED_ORIGIN` | Browser origin allowed by CORS (`*` is suitable only for local testing) |

## Install and verify

```powershell
npm ci
npm run typecheck
npm test
sam validate --lint
sam build
```

The tests use injected adapters and do not require cloud credentials. They cover request validation, UTF-8/base64 parsing, token chunking, deterministic IDs, provider response checks, pagination, re-ingestion order, no-match behavior, and HTTP error mapping.

## Run locally

After building, invoke a Lambda directly:

```powershell
sam local invoke IngestFunction -e events/ingest.json --env-vars env.local.json
sam local invoke AskFunction -e events/ask.json --env-vars env.local.json
```

Or start the API Gateway emulator:

```powershell
sam local start-api --env-vars env.local.json
```

From a second terminal:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:3000/ingest -ContentType 'application/json' -Body '{"documents":[{"id":"intro","title":"Introduction","content":"Retrieval-augmented generation grounds answers in supplied context."}]}'

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:3000/ask -ContentType 'application/json' -Body '{"question":"What grounds the answers?"}'
```

`/ask` accepts only `{ "question": "..." }`; the retrieval limit is set with `ASK_TOP_K`, rather than a public request parameter.

## Deploy

```powershell
sam deploy --guided
```

Choose a regional deployment, enter secret parameters interactively, set `AllowedOrigin` to the deployed frontend's origin, and retain the model/chunking defaults unless you have a reason to change them. The stack emits `ApiBaseUrl`; configure the frontend with this base URL.

The template configures a 90-second API Gateway REST integration and a 90-second Lambda timeout. Before deploying in a given account/region, confirm that the Regional REST API integration-timeout quota has been increased beyond 29 seconds; AWS can reduce the account throttle quota when this limit is raised.

## Responses

`POST /ingest` returns:

```json
{ "ingestedDocuments": 1, "ingestedChunks": 1 }
```

`POST /ask` returns an answer and deduplicated document sources:

```json
{ "answer": "...", "sources": [{ "docId": "intro", "title": "Introduction" }] }
```

Errors use a stable `{ "error": { "code", "message" } }` envelope. Provider error details and secrets are not returned to clients.
