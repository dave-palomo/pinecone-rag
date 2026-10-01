# Doc Q&A Portal Frontend

Thin Next.js client for the existing FastAPI document-ingestion and question-answering API.

## Requirements

- Node.js 20.9 or newer
- npm
- A reachable Doc Q&A Portal FastAPI backend

## Local setup

Install dependencies:

```bash
npm install
```

Copy `.env.example` to `.env.local` and set the backend base URL:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Start the frontend:

```bash
npm run dev
```

Open <http://localhost:3000>. The backend must be running and reachable through `NEXT_PUBLIC_API_BASE_URL`. For the default local setup, the FastAPI backend runs at `http://localhost:8000` and must allow `http://localhost:3000` through `ALLOWED_ORIGINS`.

## Pages

- `/`: minimal entry page and links to the two workflows.
- `/docs`: add one or more plain-text documents and send them to `POST /ingest`.
- `/ask`: send a question to `POST /ask` and render the answer and every returned source.

## Validation commands

```bash
npm run lint
npm run build
npm run test:e2e
```

## Vercel deployment

Create a Vercel project from this repository and configure:

- Root directory: `frontend`
- Environment variable: `NEXT_PUBLIC_API_BASE_URL=https://<backend-domain>`

The deployed backend must include the Vercel origin in `ALLOWED_ORIGINS`. Do not add `OPENAI_API_KEY`, `PINECONE_API_KEY`, or any other secret to this frontend project. Variables prefixed with `NEXT_PUBLIC_` are exposed to the browser and frozen into the bundle at build time.

## Known limitations

- The first implementation accepts plain text only; there is no file upload or document extraction.
- Answers are rendered as plain text, even when the model returns Markdown.
- There is no authentication, persistent frontend state, streaming, or chat history.
- Visual styling is intentionally restrained so backend integration remains the priority.
