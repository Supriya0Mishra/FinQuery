# FinQuery

An AI accounts-payable copilot. Upload invoices in bulk; FinQuery extracts the
fields with an LLM in the background and puts each invoice in an inbox for
review.

> **Status:** v2 rewrite in progress. Phase 1 (full-stack foundation) is in
> place; see [ROADMAP.md](ROADMAP.md) for what comes next. The original
> single-file Streamlit app lives in [legacy/streamlit](legacy/streamlit).

## What works today

- Bulk PDF upload with per-file results (accepted / duplicate / rejected)
- De-duplication by file hash, so the same file is never processed twice
- Background extraction with Celery: vendor, customer, invoice number, dates,
  currency, subtotal, tax, total, payment terms and line items
- Invoice inbox with live status and a detail page
- Retry for failed invoices

## Architecture

```
Next.js ──► FastAPI ──► PostgreSQL        (invoices, line items)
               │  └───► MinIO / S3        (original PDFs)
               └──► Redis ──► Celery worker
                               1. read PDF text (pypdf)
                               2. LLM structured output (Groq Llama 3.3 70B + Pydantic)
                               3. save fields, status -> needs_review
```

| Layer | Technology |
|---|---|
| Frontend | Next.js (App Router), TypeScript, Tailwind CSS, TanStack Query |
| API | FastAPI, Pydantic, SQLAlchemy 2, Alembic |
| Jobs | Celery + Redis |
| Storage | PostgreSQL (pgvector image), MinIO / S3 |
| AI | Groq (Llama 3.3 70B), LangChain structured output |

## Run it locally

Requires Docker Desktop and Node.js 20+.

```bash
cp .env.example .env        # then add your GROQ_API_KEY
docker compose up --build   # API on http://localhost:8000/docs
```

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev                 # http://localhost:3000
```

## Tests

```bash
cd backend
uv sync
uv run pytest
uv run ruff check .
```

The API tests use in-memory SQLite with fake storage and a fake queue, so they
need no running services.
