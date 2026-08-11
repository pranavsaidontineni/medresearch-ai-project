# MedResearch AI

AI Medical Literature Research Assistant built with React + TypeScript, FastAPI, PostgreSQL, PubMed E-Utilities, and Google Gemini.

## Features in this version

- JWT authentication with registration and login
- PubMed search with pagination-ready API
- PubMed article retrieval and abstract display
- PostgreSQL paper caching
- Search history
- Save papers
- Personal collections
- Gemini structured-output paper summaries
- Key findings and limitations extraction
- Patient-friendly explanations
- 2–5 paper AI comparison
- Responsive React UI
- Alembic database migrations

## Architecture

```text
React + TypeScript
        |
        | REST / JSON
        v
FastAPI
  |       |       |
  |       |       +--> Gemini API
  |       |
  |       +----------> PubMed E-Utilities
  |
  +------------------> PostgreSQL
```

## AI API

This project uses Google's official `google-genai` Python SDK. The Gemini API key is stored only on the backend in `backend/.env` and is never exposed to the browser.

The default model is configurable through `GEMINI_MODEL`. Because Gemini model availability and free-tier quotas can change, verify the model and quota shown for your Google AI Studio project before running AI features.

## PubMed API

The project uses NCBI E-Utilities. Set `NCBI_EMAIL` to an email associated with the application. An NCBI API key is optional for normal low-volume development; it raises the default request-rate allowance when needed.

## Run locally

1. Copy `backend/.env.example` to `backend/.env`.
2. Set a strong `JWT_SECRET_KEY`, `NCBI_EMAIL`, and `GEMINI_API_KEY`.
3. Start PostgreSQL:

```bash
docker compose up -d db
```

4. Create a Python virtual environment and install backend dependencies:

```bash
cd backend
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

5. Run migrations:

```bash
alembic upgrade head
```

6. Start FastAPI:

```bash
uvicorn app.main:app --reload
```

7. Install and start the frontend:

```bash
cd ../frontend
npm install
npm run dev
```

Backend docs: `http://localhost:8000/docs`

Frontend: `http://localhost:5173`

## Security notes

- Never commit `.env` files or API keys.
- Gemini is called only by FastAPI.
- JWTs protect application endpoints.
- User library records are scoped by authenticated user ID.
- AI prompts explicitly prohibit unsupported claims and medical advice.
- This application is a research-assistance tool, not a diagnostic or treatment system.

## Research Workspaces and Grounded Q&A

The research workspace feature turns a selected set of cached PubMed papers into a small evidence-grounded research environment:

1. Create a workspace with an optional research question.
2. Add cached papers from search results.
3. Ask a question across the selected literature.
4. Retrieve the most relevant abstract excerpts using deterministic lexical retrieval.
5. Send only those retrieved excerpts to Gemini.
6. Return a structured answer with evidence strength, uncertainty, and supporting PMIDs.

This is intentionally implemented without a paid vector database. The retrieval layer is deterministic and auditable, which is appropriate for an abstract-level MVP. A future version can add embeddings/pgvector for semantic retrieval.

### Migration

Run:

```bash
cd backend
alembic upgrade head
```

This applies migration `0003_research_workspace`.

## Research Workspace v2

The research workspace now includes a transparent hybrid retrieval baseline (TF-IDF-style cosine similarity, term coverage, overlap, and title weighting) and a Gemini-generated structured literature review. Reports are generated from the workspace's cached PubMed abstracts and are not persisted in the MVP.

New endpoint: `POST /api/v1/workspaces/{workspace_id}/literature-review`

## Production hardening in this build

- AI analysis results are cached by a SHA-256 content key so repeated requests for unchanged paper content do not repeatedly consume Gemini quota.
- Workspace questions and literature reviews are also cached using their evidence/context payloads.
- A lightweight in-process request limiter returns HTTP 429 when a client exceeds the configured per-route development limit. For horizontally scaled production deployment, replace this with a shared Redis-backed limiter.
- Security response headers are added by FastAPI middleware.
- `/health` checks PostgreSQL connectivity and reports `ok` or `degraded`.
- Dockerfiles are provided for backend and frontend, with a full `docker compose` stack for PostgreSQL, FastAPI, and Nginx-served React.
- AI keys remain backend-only; the frontend receives no Gemini credentials.

### Full Docker run

Create a root `.env` from `.env.example`, set `GEMINI_API_KEY`, `NCBI_EMAIL`, and a strong `JWT_SECRET_KEY`, then run:

```bash
docker compose up --build
```

Frontend: `http://localhost:8080`
Backend docs: `http://localhost:8000/docs`

### Tests

From `backend/`:

```bash
pytest -q
```

The repository includes unit tests for retrieval, rate limiting, cache-key stability, and JWT behavior. Full integration tests require the project dependencies and a PostgreSQL service.
