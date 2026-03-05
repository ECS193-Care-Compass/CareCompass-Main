# Next Steps: Serverless Architecture with Auth

## Proposed Architecture

**Lambda + API Calls + DynamoDB + Supabase Auth**

```
User (Vercel Frontend)
  │
  ├─ Supabase Auth (optional login)
  │     ├─ Logged in  → persistent user ID
  │     └─ Guest      → generated session ID (expires on idle)
  │
  ├─ API Gateway
  │
  └─ AWS Lambda (backend)
       ├─ Crisis Detection: keyword matching + Gemini system prompt
       ├─ Retrieval: ChromaDB (pre-built, loaded from S3 to /tmp)
       ├─ Embeddings: Google text-embedding-004 API
       ├─ LLM: Gemini 2.5 Flash API
       └─ Conversation History: DynamoDB (keyed by user/session ID)
```

---

## 1. Switch to API-Based Models

### Embeddings
- Replace local `all-MiniLM-L6-v2` with Google `text-embedding-004` API
- Pre-build ChromaDB vectorstore locally using `text-embedding-004`, then upload to S3
- Lambda loads vectorstore from S3 to `/tmp` on cold start (~1 second)

### Crisis Detection
- Remove `gooohjy/suicidal-electra` ML model
- Keep existing keyword matching (catches explicit statements)
- Add crisis detection instructions to Gemini system prompt (catches nuanced/implicit language)

### Dependencies Removed
- `torch`, `transformers`, `sentence-transformers` (~2GB)
- Deployment package drops from ~2GB to <50MB
- RAM requirement drops from ~2.5GB to ~256MB

---

## 2. Deploy Backend to Lambda

### Why Lambda Is Now Viable
- No ML models to load = no cold start problem
- Small deployment package (<50MB)
- Low RAM requirement (~256MB)
- ChromaDB vectorstore loads from S3 in <1 second

---

## 3. Conversation History with DynamoDB

### Schema

| Field | Type | Description |
|-------|------|-------------|
| `session_id` (partition key) | String | User ID (logged in) or generated session ID (guest) |
| `timestamp` (sort key) | Number | Unix timestamp of the message |
| `role` | String | `user` or `model` |
| `message` | String | Message content |
| `ttl` | Number | Auto-delete timestamp (for guest sessions) |

### How It Works
- Each `/chat` request includes a `session_id`
- Lambda reads the last 10 turns from DynamoDB for that session
- After generating a response, Lambda writes the new turn back to DynamoDB
- Replaces the current in-memory `conversation_history` list in `LLMHandler`

---

## 4. Authentication with Supabase

### Why Supabase
- Free tier: 50,000 monthly active users, built-in auth UI components
- Supports email/password, Google OAuth, magic link
- Easy to integrate with React frontend
- Provides JWT tokens that can be verified on the backend

### Two User Modes

#### Mode A: Logged-In User
1. User signs in via Supabase Auth on the frontend
2. Frontend gets a Supabase JWT containing the user's ID
3. Every `/chat` request includes the JWT in the `Authorization` header
4. Lambda verifies the JWT and uses the Supabase user ID as the `session_id`
5. Conversation history persists in DynamoDB indefinitely (or until user clears it)
6. User can close the app, come back later, and resume their conversation

#### Mode B: Guest User (No Login)
1. User skips login
2. Frontend generates a random session ID (e.g., `guest-<uuid>`)
3. Every `/chat` request includes the session ID in the header
4. Lambda uses the session ID as the DynamoDB key
5. DynamoDB TTL auto-deletes guest sessions after idle timeout (e.g., 30 minutes)
6. If the user goes idle and comes back, they start a fresh conversation

### Frontend Flow

```
App loads
  │
  ├─ Show login screen (optional)
  │     ├─ "Sign In" → Supabase Auth → get user ID → use as session_id
  │     └─ "Continue as Guest" → generate guest-<uuid> → use as session_id
  │
  └─ Chat screen
        ├─ Every request sends session_id in header
        ├─ Logged-in: history persists across sessions
        └─ Guest: history expires after idle timeout
```

### Idle Timeout (Guest Sessions)
- DynamoDB supports TTL (Time to Live) natively
- Set `ttl` field on each message to `current_time + 30 minutes`
- Each new message resets the TTL for the session
- DynamoDB automatically deletes expired records — no cleanup code needed

---

## 5. HIPAA-Compliant S3 Configuration

### Requirements
- **Encryption at rest** — enable SSE-S3 or SSE-KMS on all S3 buckets (vectorstore, documents, logs)
- **Encryption in transit** — enforce HTTPS-only access via bucket policy (deny `aws:SecureTransport = false`)
- **Access logging** — enable S3 server access logging to the logs bucket
- **Versioning** — enable bucket versioning for audit trail and data recovery
- **Block public access** — enable all four S3 Block Public Access settings on every bucket
- **IAM least privilege** — Lambda's IAM role should only have access to the specific buckets it needs (read-only for vectorstore, write for logs)
- **BAA with AWS** — sign an AWS Business Associate Agreement (required for HIPAA — free, done through AWS console under Artifact)
- **No PHI in logs** — ensure conversation content is never logged to S3; only log non-sensitive metadata (timestamp, scenario, is_crisis, docs_retrieved)
- **Retention policy** — set lifecycle rules to auto-delete logs after a defined period (e.g., 90 days)
- **DynamoDB encryption** — enable encryption at rest on the conversation history table (on by default with AWS-owned keys, upgrade to KMS for HIPAA)

### Bucket Policy Example (HTTPS-Only)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::BUCKET_NAME",
        "arn:aws:s3:::BUCKET_NAME/*"
      ],
      "Condition": {
        "Bool": { "aws:SecureTransport": "false" }
      }
    }
  ]
}
```

---

## 6. Backend Code Changes

| Current | New |
|---------|-----|
| `all-MiniLM-L6-v2` (local) | `text-embedding-004` (API call) |
| `gooohjy/suicidal-electra` (local) | Keyword matching + Gemini system prompt |
| In-memory conversation history | DynamoDB per-session history |
| No auth | Supabase JWT verification |
| FastAPI on EC2 | Lambda behind API Gateway |
| `requirements.txt` includes torch, transformers | Lightweight: google-genai, chromadb, boto3 |
| S3 buckets (no HIPAA config) | HIPAA-compliant S3 (encryption, logging, access controls) |

### Files to Modify
- `backend/src/embeddings/vector_store.py` — switch to `text-embedding-004`
- `backend/src/safety/crisis_detector.py` — remove ML model, keep keywords only
- `backend/src/generation/llm_handler.py` — replace in-memory history with DynamoDB reads/writes
- `backend/src/generation/prompt_templates.py` — add crisis detection instructions to system prompt
- `backend/api.py` — accept `session_id` header, add Supabase JWT verification
- `backend/requirements.txt` — remove torch/transformers/sentence-transformers
- `chatbot-frontend/src/renderer/src/api.ts` — send session_id, update base URL to API Gateway
- `chatbot-frontend/src/renderer/src/App.tsx` — add login/guest flow with Supabase
- AWS S3/DynamoDB — apply HIPAA-compliant encryption, logging, and access policies

---

## Summary

| Component | Current | Proposed |
|-----------|---------|----------|
| Hosting | EC2 | Lambda |
| Embeddings | Local model | Google API |
| Crisis detection | Local model | Keywords + Gemini prompt |
| Conversation history | In-memory (single user) | DynamoDB (multi-user) |
| Auth | None | Supabase (optional login) |
| Guest sessions | N/A | Auto-expire after idle |
| Frontend deploy | Local Electron | Vercel (web app) |
| S3/DynamoDB compliance | Basic | HIPAA-compliant |
