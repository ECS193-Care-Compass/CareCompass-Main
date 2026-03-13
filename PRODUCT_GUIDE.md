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

---

## Types of Questions You Can Ask

CareCompass answers questions based on its ingested knowledge base of trusted documents. Below are example questions organized by category, along with the source documents that back each topic.

### Medical Follow-Up & Forensic Exam

*Backed by: SAFE Protocol document, CDC HIV/Partner Services brochure*

- "What happens during a forensic exam?"
- "What is the SAFE protocol?"
- "When should I get tested for STIs after an assault?"
- "What is HIV prophylaxis and how does it work?"
- "What are the timelines for HIV and STI testing?"
- "Do I need to go back for follow-up appointments?"
- "What is partner services and how does it work?"

### Legal & Advocacy

*Backed by: Marsy's Law victim rights card, Survivors' Right to Time Off FAQs, Sacramento Sheriff SA pamphlet*

- "What are my rights as a survivor?"
- "What is Marsy's Law and how does it protect me?"
- "Can I take time off work because of what happened?"
- "How much time off am I entitled to?"
- "Do I have to report to the police?"
- "How do I get a protection order?"
- "What are my options if I'm not ready to report?"

### Practical & Social Needs

*Backed by: Sacramento Sheriff SA pamphlet, Survivors' Right to Time Off FAQs*

- "What local resources are available in Sacramento?"
- "Where can I find a support group?"
- "What employment rights do I have as a survivor?"
- "How do I access victim compensation?"

### Mental Health & Emotional Support

*Backed by: SAMHSA Trauma-Informed Care framework*

- "I'm having trouble sleeping since it happened"
- "I keep having flashbacks, is that normal?"
- "I feel anxious all the time and don't know what to do"
- "What does trauma-informed care mean?"
- "What are some coping strategies?"

### General Support

- "I don't know where to start"
- "I just need someone to talk to"
- "What kind of help is available to me?"

### What CareCompass Cannot Answer

CareCompass is scoped to post-sexual assault care and support. It **cannot** help with:

- Topics unrelated to survivor support (e.g., math homework, cooking recipes)
- Specific legal advice (it provides general information, not legal counsel)
- Medical diagnoses or treatment plans (it provides general guidance and referrals)
- Real-time emergency response (if you are in immediate danger, call 911)

If the bot detects a crisis, it will prioritize connecting you with emergency resources like the **988 Suicide & Crisis Lifeline** and **Crisis Text Line (text HOME to 741741)**.
