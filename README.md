# Doc Q&A Portal

This repository documents an incremental implementation of a small Retrieval-Augmented Generation (RAG) application.

The original assignment asked for a **Next.js + TypeScript frontend** connected to an **AWS API Gateway + Lambda backend written in Node.js/TypeScript**. The backend had to ingest plain-text documents, split them into chunks, generate embeddings, store and retrieve vectors with **Pinecone**, and use an LLM to answer questions grounded in the retrieved document context. The RAG flow had to be implemented directly, without LangChain, LlamaIndex, or similar frameworks.

## Why the project was divided into stages

Although the core RAG problem was familiar, several required technologies were either new or had limited prior exposure:

- Python was the primary backend language, while the requested solution required Node.js/TypeScript.
- AWS services had been used before, but not specifically the API Gateway → Lambda setup required by the assignment.
- Vector databases were familiar conceptually, but Pinecone had not been used directly.
- The final solution also required AWS SAM and Lambda-specific packaging and deployment.

Instead of introducing all of those unknowns at once, the project was divided into three **ascending prototypes**. Each stage kept previously validated parts stable while introducing the next major source of complexity.

## Branch progression

### 1. `prototype/python-fastapi-railway`

**Goal: validate the application and RAG flow using a familiar backend stack.**

The first prototype implements the backend with **Python + FastAPI**, deployed on **Railway**, while the frontend uses **Next.js + TypeScript** on Vercel.

This stage focuses on validating the end-to-end application:

```text
Next.js
   ↓
FastAPI / Python
   ↓
OpenAI + Pinecone
```

It establishes the core behavior required by the assignment: document ingestion, token-based chunking, embeddings, Pinecone storage and retrieval, prompt construction, LLM answers, source attribution, error handling, and re-ingestion behavior.

---

### 2. `prototype/python-aws-lambda-api-gateway`

**Goal: move the validated RAG implementation to the requested AWS architecture while keeping Python as the known variable.**

The second prototype replaces FastAPI/Railway with **AWS API Gateway + Lambda** and introduces **AWS SAM** for Infrastructure as Code.

```text
Next.js
   ↓
AWS API Gateway
   ↓
AWS Lambda / Python
   ↓
OpenAI + Pinecone
```

This stage isolates the AWS-specific learning: Lambda handlers, API Gateway integration, CORS, environment configuration, SAM templates, CloudFormation deployment, local Lambda execution, and dependency packaging.

The external API contract and RAG behavior remain intentionally close to the first prototype.

---

### 3. `prototype/nodejs-aws-lambda-sam`

**Goal: port the validated AWS backend from Python to the Node.js/TypeScript stack required by the assignment.**

The third prototype keeps the AWS architecture established in the previous stage and replaces the Python backend with **Node.js + TypeScript**.

```text
Next.js / TypeScript
        ↓
AWS API Gateway
        ↓
AWS Lambda / Node.js + TypeScript
        ↓
OpenAI + Pinecone
```

This branch is the **most complete implementation of the requested solution** and the closest match to the original assignment requirements.

It includes:

- Next.js + TypeScript frontend
- AWS API Gateway
- Node.js/TypeScript Lambda functions
- AWS SAM Infrastructure as Code
- OpenAI embeddings and LLM integration
- Pinecone vector storage and retrieval
- RAG implemented directly without LangChain or LlamaIndex
- Runtime request validation
- Unit tests and type checking
- Local SAM execution and AWS deployment configuration

For reviewing the final implementation, start with:

[`prototype/nodejs-aws-lambda-sam`](https://github.com/dave-palomo/pinecone-rag/tree/prototype/nodejs-aws-lambda-sam)

## Development strategy

The progression can be summarized as:

```text
1. Solve the application and RAG flow
                ↓
2. Solve the AWS infrastructure
                ↓
3. Port to the required backend language
```

Or, from a risk perspective:

```text
RAG / application uncertainty
            ↓
AWS infrastructure uncertainty
            ↓
Node.js / TypeScript uncertainty
```

This approach made it possible to validate one major concern at a time while keeping the already working parts of the system stable.

## Repository branches

| Branch | Main purpose |
|---|---|
| [`prototype/python-fastapi-railway`](https://github.com/dave-palomo/pinecone-rag/tree/prototype/python-fastapi-railway) | End-to-end RAG baseline using Python/FastAPI and Railway |
| [`prototype/python-aws-lambda-api-gateway`](https://github.com/dave-palomo/pinecone-rag/tree/prototype/python-aws-lambda-api-gateway) | AWS API Gateway + Lambda + SAM implementation while retaining Python |
| [`prototype/nodejs-aws-lambda-sam`](https://github.com/dave-palomo/pinecone-rag/tree/prototype/nodejs-aws-lambda-sam) | Final Node.js/TypeScript AWS implementation and closest match to the assignment |
| `master` | Repository overview and navigation between the implementation stages |

Each prototype branch contains its own README with implementation-specific setup, architecture, tests, deployment instructions, trade-offs, and known limitations.

## Future improvements

The current prototypes intentionally focus on the core assignment scope. The following improvements would be the next priorities for evolving the project beyond the baseline implementation.

### Product and document management

**Delete document endpoint**  
Add a dedicated API endpoint to delete every Pinecone vector associated with a `docId`. This would complete the basic document lifecycle and remove the need to clean test or obsolete documents directly from Pinecone.

**Physical file upload**  
Extend ingestion beyond plain-text form input to accept files such as PDF and DOCX. A production-oriented version could upload files through S3 and extract their text before sending it through the existing chunk → embed → store pipeline.

**Document library**  
Add a UI section that shows the documents currently indexed in the configured Pinecone namespace. Combined with document deletion, this would provide a simple management view for inspecting and maintaining the active knowledge base.

**Live word and token counter**  
Display word and token counts while users enter or upload document content. This would make chunking behavior and request size more transparent and help users understand the approximate amount of content being ingested.

### RAG quality

**Minimum retrieval similarity threshold**  
`topK` guarantees the nearest matches, but not that those matches are sufficiently relevant. Introduce a configurable minimum similarity score so weak matches can be discarded before building the RAG context. If no match passes the threshold, the backend can return a clean no-match response without calling the LLM.

**LLM answerability signal**  
Use structured LLM output with an explicit signal indicating whether the retrieved context contains enough information to answer the question. This would prevent the API from returning document sources when the model correctly determines that the available context is insufficient.

### Reliability and consistency

**Controlled retries for OpenAI and Pinecone**  
Add bounded retries with backoff for transient network failures, rate limits, and retryable provider `5xx` errors. Retry behavior should remain limited and observable so temporary provider issues do not immediately fail an entire request.

**Read-after-write handling**  
Account for the short propagation window observed after Pinecone ingestion or document replacement. Possible approaches include a short retry with backoff or an explicit indexing/ready state before treating newly written vectors as immediately queryable.

### Operational improvements

**Per-stage observability**  
Record latency and outcomes separately for tokenization, embedding generation, Pinecone operations, prompt construction, LLM generation, and total request duration. This would make bottlenecks easier to diagnose and provide evidence for tuning Lambda memory and timeout settings.

**Independent Lambda timeouts**  
Configure `/ingest` and `/ask` independently instead of applying the same timeout to both paths. Ingestion performs more variable work—tokenization, embedding batches, deletion, and upserts—while question answering normally follows a shorter retrieval-and-generation path.

