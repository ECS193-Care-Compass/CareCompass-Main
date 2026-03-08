# CareCompass (CARE Bot) — Architecture

## System Diagram

![System Diagram](System_Diagram.png)

## What It Is

A trauma-informed RAG (Retrieval-Augmented Generation) chatbot for sexual assault survivors. Users ask questions and get responses grounded in authoritative documents (SAMHSA trauma-informed care framework, CDC HIV/testing resources) with built-in crisis safety.

## Tech Stack

- **Frontend**: Electron + React + TypeScript + Tailwind CSS 4
- **API**: FastAPI (Python), served via Uvicorn (local) or AWS Lambda (production)
- **LLM**: Google Gemini 2.5 Flash (via `google-genai` SDK)
- **Vector DB**: ChromaDB (persistent, local storage / S3-backed on Lambda)
- **Embeddings**: Google `gemini-embedding-001` (768-dim, via Gemini API)
- **Crisis Detection**: Keyword matching + Gemini inline assessment (structured JSON output)
- **Authentication**: Supabase (JWT-based, with guest fallback)
- **Conversation History**: AWS DynamoDB (per-session, TTL auto-expiry for guests)
- **Logging**: AWS S3 (API interaction audit trail)
- **Infrastructure**: AWS CloudFormation (Lambda, API Gateway, DynamoDB, IAM)

## Authentication Flow

```
User opens app
  │
  ├─ Sign In / Sign Up → Supabase Auth → JWT token
  │     └─ JWT sent as Authorization: Bearer <token> on every API call
  │     └─ Backend verifies JWT, extracts user ID as session_id
  │
  └─ Guest Mode → Frontend generates guest-<uuid>
        └─ session_id sent in request body
        └─ DynamoDB TTL auto-expires guest sessions (30 min)
```

## Document Ingestion Pipeline

1. **Source PDFs** placed in `data/raw/` (SAMHSA framework doc, CDC HIV brochures)
2. **PDF extraction** — page-by-page text extraction via `pypdf`
3. **Chunking** — 500-token chunks with 50-token overlap
4. **Metadata tagging** — each chunk gets `source`, `page`, `category`, `scenario_type`, `document_type`
5. **Embedding + storage** — Google Gemini embedding API embeds chunks and ChromaDB stores them persistently at `data/processed/vectorstore/`

The vector store auto-initializes on first API startup if empty.

## Request Pipeline (per user message)

```
User query + session_id (from JWT or guest UUID)
  │
  ├─ 1. Crisis Detection — Keywords (runs FIRST, before RAG)
  │     └─ Keyword matching (~30 phrases for suicidal/self-harm language)
  │     → If keywords match, crisis emphasis is prepended to prompt
  │
  ├─ 2. Retrieval
  │     ├─ Query embedded via Gemini embedding API (gemini-embedding-001)
  │     ├─ ChromaDB cosine similarity search (top-k=3, threshold=0.7)
  │     └─ Optional scenario filtering (e.g., "immediate_followup", "mental_health")
  │
  ├─ 3. Prompt Construction
  │     ├─ Trauma-informed system prompt (SAMHSA's 6 principles baked in)
  │     ├─ Retrieved document context injected
  │     ├─ Crisis assessment instruction included (Gemini evaluates every message)
  │     └─ JSON output format enforced: {"response": "...", "is_crisis": true/false}
  │
  ├─ 4. LLM Generation
  │     ├─ Google Gemini 2.5 Flash API call (temp=0.7, max 4096 tokens, JSON mode)
  │     ├─ Conversation history from DynamoDB (max 10 turns per session)
  │     └─ Fallback response with hotline numbers if API fails or safety filters block
  │
  ├─ 5. Crisis Signal Merge
  │     └─ final_is_crisis = keyword_triggered OR gemini_is_crisis
  │
  └─ 6. Logging
        ├─ Conversation turn saved to DynamoDB (user message + bot response)
        └─ Interaction logged to S3 (audit trail)
```

## Crisis Safety Design

- **Layer 1 — Keywords**: Fast keyword matching runs before retrieval to catch explicit suicidal/self-harm statements. If triggered, crisis protocol instructions are prepended to the prompt.
- **Layer 2 — Gemini inline assessment**: Every prompt instructs Gemini to assess the message for crisis signals (direct or indirect) and return `is_crisis` in its structured JSON response. This catches implicit/nuanced expressions that keywords miss — with no extra API call since Gemini is already being called.
- **Signal merging**: `is_crisis = keyword_triggered OR gemini_detected`. Either layer triggering activates crisis mode.
- If Gemini fails during a crisis, a hardcoded fallback with hotline numbers is returned.

## Data Storage

| Store | What | Persistence |
|-------|------|-------------|
| **ChromaDB** | Document embeddings + metadata | Local (`data/processed/vectorstore/`) or `/tmp` on Lambda (restored from S3) |
| **DynamoDB** | Conversation history (per session) | TTL auto-expires guest sessions (30 min). Authenticated user sessions persist longer. |
| **S3 (logs)** | API interaction audit trail | Permanent (date-partitioned JSON files) |
| **S3 (vectordb)** | Vectorstore backup (.zip) | Used by Lambda cold start to restore ChromaDB |
| **S3 (documents)** | Raw source PDFs | Permanent |

## AWS Lambda Architecture

```
Electron Frontend
    ↓ (HTTPS)
API Gateway (care-compass-api-dev)
    ↓
Lambda Function (care-compass-dev)
    ├─ Cold start: download vectorstore.zip from S3 → extract to /tmp/vectorstore/
    ├─ Warm invocations: reuse /tmp (no re-download)
    ├─ Process query through RAG pipeline
    ├─ Read/write conversation history → DynamoDB
    └─ Log interactions → S3

Supporting Resources:
    ├─ DynamoDB: care-compass-conversations-dev (conversation history)
    ├─ S3: care-compass-vectordb-*-dev (vectorstore backup)
    ├─ S3: care-compass-logs-*-dev (interaction logs)
    ├─ S3: care-compass-documents-*-dev (raw PDFs)
    └─ IAM Role with S3 + DynamoDB access policies
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/chat` | POST | Main chat — takes `{query, scenario?, session_id?}` + optional `Authorization` header, returns `{response, is_crisis, num_docs_retrieved, blocked}` |
| `/clear` | POST | Reset conversation history for a session |
| `/health` | GET | Health check |
| `/stats` | GET | Vector store count, model info, history stats |
| `/categories` | GET | List of 5 scenario categories |

## Scenario Categories

Five predefined categories users can select to filter retrieval:

- **Medical Follow-Up** — STI/HIV testing, medical appointments, prophylaxis
- **Mental Health Support** — Counseling, anxiety, sleep issues, trauma support
- **Practical & Social Needs** — Housing, transportation, financial assistance
- **Legal & Advocacy** — Legal help, protection orders, reporting options
- **Delayed Follow-Up** — It's been a while, not sure if it still matters

## Key Config (tunable via `.env`)

| Parameter | Default |
|-----------|---------|
| `MODEL_NAME` | gemini-2.5-flash |
| `EMBEDDING_MODEL` | gemini-embedding-001 |
| `TOP_K` | 3 |
| `SIMILARITY_THRESHOLD` | 0.7 |
| `CHUNK_SIZE` | 500 |
| `CHUNK_OVERLAP` | 50 |
| `TEMPERATURE` | 0.7 |
| `MAX_OUTPUT_TOKENS` | 4096 |
| `DYNAMODB_TABLE_NAME` | care-compass-conversations |
| `DYNAMODB_TTL_MINUTES` | 30 |
| `MAX_HISTORY_TURNS` | 10 |

## Key Source Layout

- `backend/api.py` — FastAPI server with Supabase JWT auth
- `backend/main.py` — `CAREBot` class, orchestrates the RAG pipeline
- `backend/src/auth/supabase_auth.py` — JWT verification
- `backend/src/safety/crisis_detector.py` — Keyword-based crisis detection
- `backend/src/embeddings/document_processor.py` — PDF extraction and chunking
- `backend/src/embeddings/vector_store.py` — ChromaDB wrapper (Gemini embeddings, S3 restore on Lambda)
- `backend/src/retrieval/retriever.py` — Semantic search with optional scenario filtering
- `backend/src/generation/llm_handler.py` — Gemini API (JSON mode), DynamoDB conversation history
- `backend/src/generation/prompt_templates.py` — Trauma-informed prompt construction
- `backend/src/utils/dynamodb_history.py` — DynamoDB conversation history (with in-memory fallback)
- `backend/src/utils/backup_scheduler.py` — Weekly ChromaDB → S3 backups
- `backend/config/settings.py` — All tuneable parameters
- `backend/config/trauma_informed_principles.py` — SAMHSA's 6 principles, scenario categories, crisis keywords
- `aws/lambda/lambda_handler.py` — Lambda handler (session_id + auth support)
- `aws/infrastructure/template.yaml` — CloudFormation template (Lambda, API Gateway, DynamoDB, IAM)
- `aws/deployment/deploy.ps1` — PowerShell deployment script (uses AWS CLI, no SAM CLI needed)
- `aws/scripts/upload_vectorstore.py` — Upload local vectorstore to S3 for Lambda