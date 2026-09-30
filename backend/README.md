# Doc Q&A Portal API

FastAPI backend for plain-text ingestion and retrieval-augmented question answering.

## Local setup

From the repository root:

```powershell
python -m venv backend/.venv
backend\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend/requirements-dev.txt
Copy-Item backend/.env.example backend/.env
```

Populate `backend/.env` with your own OpenAI and Pinecone credentials. Never
commit that file.

The Pinecone index must already exist as a dense vector index using cosine
similarity and the dimension configured by `EMBEDDING_DIMENSIONS` (1536 by
default). Its metadata configuration must allow filtering on `docId`, because
document replacement deletes prior vectors using that field.

Run the API:

```powershell
Set-Location backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger UI is available at `http://localhost:8000/docs` and the health check at
`http://localhost:8000/health`.

## Tests

Tests use fakes and do not call OpenAI or Pinecone:

```powershell
Set-Location backend
python -m pytest
```

## Example requests

```powershell
$body = @{
  documents = @(
    @{
      id = "refund-policy"
      title = "Refund Policy"
      content = "Full refund within 30 days with receipt."
    }
  )
} | ConvertTo-Json -Depth 4

Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/ingest `
  -ContentType application/json `
  -Body $body
```

```powershell
$body = @{ question = "Can I get a refund?" } | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/ask `
  -ContentType application/json `
  -Body $body
```

## Railway

Create a Railway service with `backend/` as its root directory. Install from
`requirements.txt` and start with `python -m app`. The process binds to
`0.0.0.0` and prefers Railway's `PORT` variable over local `APP_PORT`.

Configure every variable from `.env.example` in Railway. Set
`ALLOWED_ORIGINS` to the deployed frontend origin.

## Prototype trade-offs

- Multi-document ingestion is sequential and not request-wide transactional.
  Documents completed before a later failure remain committed.
- New embeddings are generated before old vectors are deleted, but Pinecone
  replacement is not transactional. A delete/upsert failure can temporarily
  remove or partially replace a document.
- Pinecone index provisioning, authentication, file extraction, reranking,
  hybrid retrieval, and AWS infrastructure are outside this branch.

## If I had more time

- Add integration tests against dedicated OpenAI and Pinecone test resources.
- Add idempotency keys and versioned namespaces for atomic document promotion.
- Add structured logging, tracing, rate limits, and request-size limits.
- Add evaluation datasets for retrieval and grounded-answer quality.
