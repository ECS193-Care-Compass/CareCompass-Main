# AWS Hosting: Cost & Architecture Comparison

## The Two Approaches

| | **Approach A: Local Models + EC2** | **Approach B: All API Calls + Lambda** |
|--|-----------------------------------|---------------------------------------|
| Embedding | `all-MiniLM-L6-v2` (runs on EC2) | Google `text-embedding-004` (API call) |
| Crisis Detection | `gooohjy/suicidal-electra` (runs on EC2) | Keyword matching + Gemini system prompt |
| LLM | Gemini 2.5 Flash (API call) | Gemini 2.5 Flash (API call) |
| Vector Store | ChromaDB on EBS disk | ChromaDB pre-built, loaded from S3 |
| Hosting | EC2 instance (always running) | Lambda (runs only when called) |

---

## Approach A: Local Models on EC2

### Why EC2 Is Required

The two local ML models make Lambda impractical:

1. **`all-MiniLM-L6-v2`** (~80MB) — needed at query time to embed the user's message for ChromaDB similarity search. Must stay loaded in memory.

2. **`gooohjy/suicidal-electra`** (~400MB) — needed at query time to classify every incoming message for suicidal ideation. Must stay loaded in memory.

3. **`torch` + `transformers`** — required dependencies for both models. Adds ~1.5GB to the deployment package and ~2GB RAM at runtime.

**Why this breaks Lambda:**
- Lambda has a **10GB container image limit** — fits, but barely
- Lambda cold starts would **re-download and load both models every time** the function scales down (10-30 seconds of latency)
- Lambda's `/tmp` is **ephemeral** — ChromaDB vectorstore would need to be re-loaded from S3 on every cold start
- Combined RAM usage (~2.5GB) requires a high-memory Lambda config ($$$)
- **Conversation history** is stored in-memory (up to 10 turns) — Lambda is stateless, so history would be lost between invocations

An EC2 instance solves all of these: models load once at boot, ChromaDB persists on disk, conversation history stays in memory, and there's no cold start.

### EC2 Cost Breakdown

**Instance: `t3.medium` (2 vCPU, 4GB RAM) — minimum viable for both models**

| Resource | Monthly Cost |
|----------|-------------|
| t3.medium On-Demand | $30.37 |
| EBS 30GB gp3 | $2.40 |
| Elastic IP | $0 (free while attached) |
| Data transfer (first 100GB free) | ~$0 |
| **Total** | **~$33/mo** |

With a 1-year reserved instance: **~$21/mo**

**Plus API costs (same in both approaches):**

| API | Cost |
|-----|------|
| Gemini 2.5 Flash input | $0.15 / 1M tokens |
| Gemini 2.5 Flash output | $0.60 / 1M tokens |
| Estimated per message (~1K in, ~500 out) | ~$0.00045 |
| 1,000 messages/month | ~$0.45 |
| 10,000 messages/month | ~$4.50 |

**Total Approach A: ~$33-38/mo**

---

## Approach B: All API Calls on Lambda

### What Changes

1. **Embeddings** — replace local `all-MiniLM-L6-v2` with Google's `text-embedding-004` API
   - Same quality (actually better: 768-dim vs 384-dim)
   - No model to load, no `torch`, no `sentence-transformers`

2. **Crisis detection** — replace local `suicidal-electra` with:
   - Keyword matching (already exists, zero cost, catches explicit statements) and Gemini system prompt instructions (catches nuanced/implicit crisis language — no extra API call since Gemini is already being called for every message)

3. **Hosting** — Lambda becomes viable because:
   - No ML models to load = no cold start problem
   - Deployment package drops from ~2GB to <50MB
   - RAM needed drops from ~2.5GB to ~256MB
   - ChromaDB vectorstore (~50MB) loads from S3 to `/tmp` in <1 second

4. **Conversation history** — store in DynamoDB (free tier: 25GB storage, 25 read/write capacity units) or accept stateless sessions

### Lambda Cost Breakdown

| Resource | Monthly Cost |
|----------|-------------|
| Lambda (first 1M requests/mo free) | $0 |
| Lambda compute (400K GB-seconds free) | $0 |
| API Gateway (first 1M calls free) | $0 |
| S3 (vectorstore, <1GB) | $0.02 |
| DynamoDB (conversation history, free tier) | $0 |
| **Infrastructure total** | **~$0** |

**API costs:**

| API | Cost |
|-----|------|
| Gemini 2.5 Flash (same as Approach A) | ~$0.00045/message |
| Google text-embedding-004 (free tier: 1,500 req/day) | $0 |
| text-embedding-004 (paid, if over free tier) | $0.006 / 1M characters |
| Estimated embedding cost per message (~200 chars) | ~$0.0000012 |
| **Total per message** | **~$0.00045** |

| Traffic | Monthly API Cost |
|---------|-----------------|
| 1,000 messages | ~$0.45 |
| 10,000 messages | ~$4.50 |
| 100,000 messages | ~$45 |

**Total Approach B: ~$0-5/mo at typical usage**

---

## Side-by-Side Comparison

| Factor | Approach A (EC2 + Local Models) | Approach B (Lambda + API Calls) |
|--------|--------------------------------|--------------------------------|
| **Monthly cost (low traffic)** | ~$33 | ~$0 |
| **Monthly cost (moderate traffic)** | ~$38 | ~$5 |
| **Monthly cost (high traffic)** | ~$43 | ~$45 |
| **Cold start latency** | None (always running) | ~2-3s (first request after idle) |
| **Per-request latency** | ~1-2s (local inference + Gemini API) | ~1-2s (embedding API + Gemini API) |
| **Deployment complexity** | SSH, systemd, Nginx, OS updates | Upload ZIP, done |
| **Scaling** | Manual (or set up Auto Scaling Group) | Automatic |
| **Maintenance** | Patch OS, monitor instance, restart on crash | None (AWS managed) |
| **Dependencies** | torch, transformers, sentence-transformers (~2GB) | google-genai, chromadb (~50MB) |
| **Crisis detection quality** | Keyword matching + ELECTRA model | Keyword matching + Gemini (likely better) |
| **Conversation history** | In-memory (simple) | DynamoDB or stateless |
| **Offline capability** | Models run without internet (except Gemini) | Fully dependent on internet |

---

## Recommendation

**Approach B (Lambda + API calls)** is the clear winner for this project:

- **30x cheaper** at low traffic ($0 vs $33/mo)
- **Simpler** — no server management, no SSH, no OS patching
- **Better crisis detection** — Gemini understands nuance better than the small ELECTRA model
- **Auto-scales** — handles traffic spikes without config
- **Less code** — remove ~200 lines of crisis detector ML code, remove torch/transformers dependencies

The only advantage of Approach A is zero cold start and offline model inference, neither of which matter for a cloud-hosted chatbot.
