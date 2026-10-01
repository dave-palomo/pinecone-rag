# Python RAG Improvements

Status: proposals under review.

## 1. Similarity threshold

Add a minimum similarity/relevance threshold after Pinecone retrieval so weak nearest-neighbor matches are discarded before building the RAG context.

Goal:
- reduce irrelevant context;
- avoid unrelated sources;
- improve no-match behavior.

Status: Pending detailed review.

## 2. Read-after-write handling

Add handling for the short propagation window observed immediately after ingestion, where a newly upserted vector may not be retrievable right away.

Possible approaches to evaluate:
- short retry with backoff;
- explicit indexing/ready state;
- frontend delay only if backend handling is unnecessary.

Status: Pending detailed review.

## 3. Delete document endpoint

Add an API endpoint that deletes all Pinecone vectors belonging to a document by `docId` within the configured namespace.

Goal:
- remove test documents;
- support document lifecycle management;
- avoid direct manual Pinecone cleanup.

Status: Pending detailed review.

## 4. Separate Lambda timeouts

Use independent timeout values for ingestion and question answering instead of one global Function timeout.

Reason:
- `/ingest` performs tokenization, embedding generation, delete, and upsert operations;
- `/ask` normally performs one query embedding, Pinecone retrieval, and one LLM request;
- the two paths have different latency profiles.

Status: Pending detailed review.

## 5. Controlled retries for OpenAI and Pinecone

Add bounded retries with backoff for transient provider failures such as temporary network errors, rate limits, and retryable 5xx responses.

Goal:
- improve resilience to short-lived provider failures;
- avoid failing an entire request on the first transient error;
- keep retry behavior bounded and observable.

Status: Pending detailed review.

## 6. Per-stage observability

Measure and log latency and outcome by major processing stage instead of only total request duration.

Suggested stages:
- chunking/tokenization;
- OpenAI embeddings;
- Pinecone delete/upsert/query;
- prompt construction;
- OpenAI LLM generation;
- total request duration.

Goal:
- identify bottlenecks;
- tune Lambda timeouts and memory using evidence;
- diagnose provider or retrieval latency more quickly.

Status: Pending detailed review.

## Review process

Review each proposal individually before implementation. Add technical design, trade-offs, configuration changes, tests, and acceptance criteria only after the proposal is approved.
