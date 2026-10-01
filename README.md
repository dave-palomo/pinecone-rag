# Doc Q&A Portal — Python AWS Lambda prototype

This repository contains a direct retrieval-augmented generation (RAG) backend
implemented with two native Python 3.12 AWS Lambda handlers:

- `POST /ingest` chunks plain-text documents, creates OpenAI embeddings, and
  replaces the corresponding vectors in Pinecone.
- `POST /ask` embeds a question, retrieves relevant Pinecone chunks, and asks
  an OpenAI model to answer using only that context.

AWS API Gateway and both functions are declared in `backend/template.yaml` with
AWS SAM. The implementation deliberately does not use FastAPI, Mangum,
LangChain, or LlamaIndex.

## Configuration

For direct local Python execution, edit the ignored file `backend/.env`. Keep
`backend/.env.example` as the committed reference. For SAM-local execution,
edit the ignored `backend/env.local.json`; its committed reference is
`backend/env.local.example.json`.

Required provider settings:

- `OPENAI_API_KEY`
- `OPENAI_LLM_MODEL`
- `PINECONE_API_KEY`
- `PINECONE_INDEX`

The Pinecone index must already exist as a dense, cosine-similarity index whose
dimension matches `EMBEDDING_DIMENSIONS` (1536 by default). Ingestion and search
must use the same `PINECONE_NAMESPACE`.

Never commit `.env`, `env.local.json`, API keys, or a `samconfig.toml` containing
secret parameter values.

## Install and test on Windows

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest
```

## SAM validation and local API

Docker Desktop must be running because `tiktoken` contains platform-specific
components and the deployment package must target Amazon Linux 2023.
The custom SAM `Makefile` copies only `lambdas/`, `shared/`, and production
dependencies into each artifact, so local `.env`, `env.local.json`, tests, and
documentation cannot be included in a Lambda deployment package.

```powershell
cd backend
sam validate
sam validate --lint
sam build --use-container
sam local invoke IngestFunction -e events/ingest.json --env-vars env.local.json
sam local invoke AskFunction -e events/ask.json --env-vars env.local.json
sam local start-api --env-vars env.local.json
```

Local routes:

- `POST http://127.0.0.1:3000/ingest`
- `POST http://127.0.0.1:3000/ask`

Deploy the first stack with `sam deploy --guided`. The resulting
`ApiBaseUrl` CloudFormation output is the frontend's API base URL.

## Accepted replacement trade-off

Re-ingestion embeds all new chunks before deleting old vectors. Pinecone does
not provide a transaction spanning the subsequent delete and upsert, so a
failure in that small window can temporarily remove or partially replace a
document. This is accepted for the synchronous prototype. Large documents and
asynchronous S3/SQS ingestion are outside its scope.
