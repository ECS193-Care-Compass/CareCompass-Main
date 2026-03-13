# CareCompass (CARE Bot) — Product Guide

## What is CareCompass?

CareCompass (CARE Bot) is a **trauma-informed chatbot** designed to support sexual assault survivors. It uses Retrieval-Augmented Generation (RAG) to provide compassionate, evidence-based responses grounded in SAMHSA's six trauma-informed care principles: Safety, Trustworthiness, Peer Support, Collaboration, Empowerment, and Cultural Awareness.

The bot can assist survivors with:

- **Mental Health Support** — Counseling referrals, coping strategies, trauma validation
- **Practical & Social Needs** — Housing, transportation, financial assistance
- **Legal & Advocacy Help** — Protection orders, reporting options, victim rights
- **Medical Follow-Up** — STI/HIV information, forensic exam guidance
- **Delayed Follow-Up** — Non-judgmental re-engagement for survivors returning after time has passed

CareCompass includes built-in **crisis detection** that identifies when a user may be in immediate danger and surfaces emergency resources (988 Suicide & Crisis Lifeline, Crisis Text Line).

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DOCUMENT INGESTION                          │
│                                                                     │
│  PDFs (data/raw/)                                                   │
│    → Page-by-page text extraction (pypdf)                           │
│    → Chunking (500 tokens, 50-token overlap)                        │
│    → Embedding via Google Gemini (gemini-embedding-001, 768-dim)    │
│    → Stored in ChromaDB (local vectorstore)                         │
│    → Uploaded to S3 for Lambda cold-start restore                   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION                            │
│                                                                     │
│  Electron + React Frontend (Desktop App)                            │
│    │                                                                │
│    ├── Supabase Auth ──→ JWT-based sign-in / sign-up                │
│    │                     (or guest mode with session UUID)           │
│    │                                                                │
│    └── POST /chat ─────→ FastAPI Backend (local)                    │
│                          OR API Gateway → AWS Lambda (deployed)     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        BACKEND PIPELINE                             │
│                                                                     │
│  1. Session Resolution                                              │
│     JWT user_id (authenticated) or guest-<uuid> (guest mode)        │
│                                                                     │
│  2. Crisis Detection (Pre-Retrieval)                                │
│     Keyword matching for direct crisis signals                      │
│     (e.g., "kill myself", "want to die", "self-harm")              │
│                                                                     │
│  3. Document Retrieval                                              │
│     ChromaDB vector similarity search (top-3, cosine distance)      │
│     Optional scenario-based filtering                               │
│                                                                     │
│  4. Prompt Construction                                             │
│     Trauma-informed system prompt + retrieved context                │
│     + conversation history + crisis emphasis (if triggered)         │
│                                                                     │
│  5. LLM Generation                                                  │
│     Google Gemini API (gemini-2.5-flash, JSON mode)                 │
│     Returns: {response, is_crisis}                                  │
│                                                                     │
│  6. Crisis Signal Merge                                             │
│     Final is_crisis = keyword_triggered OR gemini_is_crisis         │
│                                                                     │
│  7. Logging & History                                               │
│     Save turn → DynamoDB (conversation history, 30-min TTL)         │
│     Log interaction → S3 (audit trail, date-partitioned JSON)       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        DATA STORAGE                                 │
│                                                                     │
│  Supabase ──────── User authentication (JWT tokens)                 │
│  ChromaDB ──────── Document embeddings (local or /tmp on Lambda)    │
│  DynamoDB ──────── Conversation history per session (auto-expires)  │
│  S3 (logs) ─────── API interaction audit trail                      │
│  S3 (vectordb) ─── Vectorstore backup for Lambda cold start         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Required API Keys & Environment Variables

The following credentials are required to run CareCompass:

### Backend (`.env` in project root)

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Google Gemini API key — powers both the LLM (gemini-2.5-flash) and embedding model (gemini-embedding-001) |
| `SUPABASE_JWT_SECRET` | Yes | Supabase JWT secret for verifying user authentication tokens |
| `AWS_ACCESS_KEY_ID` | For AWS features | AWS credentials for DynamoDB, S3 logging, and Lambda deployment |
| `AWS_SECRET_ACCESS_KEY` | For AWS features | AWS credentials (paired with access key above) |
| `AWS_REGION` | For AWS features | AWS region (default: `us-east-1`) |

### Frontend (`chatbot-frontend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_SUPABASE_URL` | Yes | Your Supabase project URL (e.g., `https://xxxxx.supabase.co`) |
| `VITE_SUPABASE_ANON_KEY` | Yes | Supabase anonymous/public key for client-side auth |

### Optional Tuning Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_NAME` | `gemini-2.5-flash` | Gemini model for response generation |
| `TEMPERATURE` | `0.7` | LLM response creativity (0.0–1.0) |
| `TOP_K` | `3` | Number of documents retrieved per query |
| `SIMILARITY_THRESHOLD` | `0.7` | Minimum similarity score for retrieved documents |
| `MAX_OUTPUT_TOKENS` | `4096` | Maximum response length |
| `ENABLE_CRISIS_DETECTION` | `true` | Toggle keyword-based crisis detection |
| `DYNAMODB_TABLE_NAME` | `care-compass-conversations` | DynamoDB table for chat history |
| `DYNAMODB_TTL_MINUTES` | `30` | How long conversation history is retained |
| `MAX_HISTORY_TURNS` | `10` | Number of past turns included in context |

---

## Application Features

### Authentication

Users can access CareCompass in three ways:

- **Sign in with email** — Existing users authenticate via Supabase (email + password)
- **Create an account** — New users sign up with email verification
- **Continue as guest** — No account required; a temporary session ID (`guest-<uuid>`) is generated. Guest sessions expire after 30 minutes

### Chat Interface

- **Welcome message** — "Hello, you're safe here. I'm here to listen and provide support."
- **Guided scenario buttons** — Three quick-start options:
  - Mental Health Support
  - Practical Needs Help
  - Legal & Advocacy Help
- **Markdown-rendered responses** — Bot responses support formatted text
- **Conversation history** — The bot remembers context within a session (up to 10 turns)
- **Loading indicator** — Animated "Thinking..." with bouncing dots while the bot processes

### Crisis Detection

When the bot detects a user may be in crisis (via keywords or LLM assessment), the response prioritizes immediate safety resources:

- **988 Suicide & Crisis Lifeline** (call or text 988)
- **Crisis Text Line** (text HOME to 741741)

Crisis detection uses a two-layer approach: fast keyword matching before retrieval, plus LLM-based assessment of implicit signals like hopelessness or desperation.

### Quick Exit

A safety feature for users who need to leave the application immediately:

- **Quick Exit button** — Always visible in the top bar; instantly redirects to Google.com
- **ESC key shortcut** — Press Escape at any time to trigger quick exit
- Designed for situations where a user needs to quickly hide the application

### Resources Section

Scrolling below the chat reveals a **local resources directory** with contact information:

| Organization | Phone | Services |
|-------------|-------|----------|
| National Domestic Violence Hotline | 1-800-799-7233 | 24/7 support, crisis intervention, safety planning |
| WEAVE (Women Escaping A Violent Environment) | 916-920-2952 | Emergency shelter, counseling, support groups (24/7 crisis line) |
| My Sister's House | 916-428-3271 | Transitional housing, supportive services |
| Family Justice Center (Sacramento) | 916-874-7233 | Legal, medical, and advocacy support |
| Legal Services of Northern California | 916-551-2150 | Free legal assistance for survivors |

- Phone numbers are clickable (opens phone dialer)
- Website links open in a new tab
- National Domestic Violence Hotline highlighted as available in 200+ languages

### Sign Out

Authenticated users can sign out via the button in the top bar (next to Quick Exit). Guest users do not see a sign-out button — their session simply expires.
