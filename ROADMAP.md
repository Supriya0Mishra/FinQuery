# FinQuery v2 roadmap

Goal: turn FinQuery from a single-PDF Streamlit demo into a full-stack **AI
accounts-payable copilot**: bulk invoice ingestion, AI extraction with
GST-aware validation, human review, and an agent that answers questions across
all invoices.

Each step is small enough to finish in one or two sittings and ends with
something you can demo. "Learn" is the concept to study while building it.

## Phase 1: Foundation (full-stack skeleton)

- [x] **1.1 Monorepo layout.** `backend/`, `frontend/`, `legacy/streamlit/`, `docker-compose.yml`.
- [x] **1.2 Infrastructure.** Postgres (pgvector image), Redis, MinIO in Docker Compose.
- [x] **1.3 Data model + migrations.** `invoices`, `line_items` tables with Alembic.
- [x] **1.4 Upload API.** `POST /api/invoices` (multi-file), PDF check, size limit,
      SHA-256 de-duplication, file stored in S3/MinIO.
- [x] **1.5 Background extraction.** Celery task: read PDF, LLM structured output,
      save fields, status `queued → processing → needs_review | failed`, retries
      with backoff for transient errors.
- [x] **1.6 Read API.** List (status filter, pagination), detail, original file, retry.
- [x] **1.7 Frontend inbox.** Next.js: drag-and-drop upload, invoice table with live
      status, invoice detail page.
- [x] **1.8 Tests.** API tests on SQLite with fake storage and queue.
- [ ] **1.9 Sample data.** 10-15 public/synthetic invoices in `data/sample_invoices/`
      (digital, multi-page, GST, non-GST). Never real client documents.
- [ ] **1.10 CI.** GitHub Actions: ruff + pytest (backend), eslint + tsc (frontend).

Learn: REST design, background jobs and why they exist, idempotency, structured output.

## Phase 2: Review and validation (the "don't trust the LLM" phase)

- [ ] **2.1 Typed values.** Parse amounts (Indian and Western formats) and dates into
      numeric/date columns next to the raw strings. Unit-test the parsers heavily.
- [ ] **2.2 Validation engine.** Rules that each produce a pass/warn/fail finding:
      line items sum to subtotal, subtotal + tax = total, GSTIN format + checksum,
      CGST+SGST vs IGST consistency, due date after issue date.
- [ ] **2.3 Extend the schema.** GSTINs (vendor/customer), CGST/SGST/IGST amounts,
      HSN/SAC codes, place of supply.
- [ ] **2.4 Duplicate detection.** Same vendor + invoice number, and near-duplicates
      (same vendor + total + date) flagged for review.
- [ ] **2.5 Review screen.** PDF viewer on the left, editable fields on the right,
      validation findings highlighted, Approve / Reject.
- [ ] **2.6 Source highlighting.** Locate each extracted value in the PDF text layer
      and highlight it when the field is focused.
- [ ] **2.7 Corrections log.** Every human edit stored as (field, model value, human
      value). This becomes the evaluation dataset in Phase 4.

Learn: where LLMs fail, combining deterministic rules with AI, human-in-the-loop design.

## Phase 3: Ask FinQuery (agent across all invoices)

- [ ] **3.1 Chunk + embed.** On approval, chunk the document text and store embeddings
      in pgvector with invoice/page metadata.
- [ ] **3.2 Hybrid retrieval.** Postgres full-text search + vector search, merged with
      reciprocal rank fusion. Answers cite invoice and page.
- [ ] **3.3 Text-to-SQL tool.** Read-only DB role, allow-listed tables, row limit,
      statement timeout. For questions about numbers ("GST paid in March").
- [ ] **3.4 LangGraph agent.** Routes between `sql_query`, `search_documents`,
      `get_invoice`. Conversation memory per chat.
- [ ] **3.5 Streaming chat UI.** Server-sent events, tool-call steps shown, citations
      link to the invoice.
- [ ] **3.6 Dashboard.** Spend by vendor and month, tax totals, upcoming and overdue
      payments.

Learn: RAG in depth, tool calling, agents vs. fixed workflows, text-to-SQL safety.

## Phase 4: Production quality

- [ ] **4.1 Evaluation suite.** Labelled invoices, field-level accuracy report, run in
      CI. Record the baseline, then measure every change against it.
- [ ] **4.2 Observability.** Langfuse traces for every LLM call: prompt, latency,
      tokens, cost.
- [ ] **4.3 OCR.** Scanned and photographed invoices via a vision model, with
      Tesseract as fallback.
- [ ] **4.4 Auth and tenancy.** Organisations, users, roles; every query scoped to
      the organisation.
- [ ] **4.5 Long documents.** Replace truncation with page-wise extraction and merge.
- [ ] **4.6 Deploy.** Frontend on Vercel, API + worker on Render/Railway, managed
      Postgres. Live demo link.
- [ ] **4.7 Showcase.** README with architecture diagram, eval numbers, 2-minute demo
      video.

Learn: evals, tracing, cost/latency trade-offs, prompt-injection and data-isolation risks.
