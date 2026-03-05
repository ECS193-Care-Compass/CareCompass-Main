# EC2 Deployment Proposal for CARE Bot

## Why EC2 Instead of Lambda

The backend runs two ML models that need to stay loaded in memory:

| Model | Size | Purpose |
|-------|------|---------|
| `all-MiniLM-L6-v2` | ~80MB | Embedding user queries for ChromaDB vector search |
| `gooohjy/suicidal-electra` | ~400MB | Crisis detection (suicidal ideation classifier) |

Lambda's cold start would re-download and load these models on every invocation (10-30s latency), making it impractical. An EC2 instance keeps them loaded in memory for instant inference.

Additionally:
- **Conversation history** is stored in-memory (up to 10 turns) — Lambda is stateless and would lose it
- **ChromaDB** needs persistent disk storage — Lambda's `/tmp` is ephemeral
- FastAPI runs as a long-lived server, which maps naturally to EC2

## Recommended Instance

**`t3.medium`** — 2 vCPU, 4 GB RAM, Ubuntu 22.04

This comfortably fits both models + ChromaDB + FastAPI with room to spare. No GPU needed — the ELECTRA crisis model runs fast enough on CPU for single-user inference.

## Cost Comparison

| Option | Spec | Monthly Cost | Notes |
|--------|------|-------------|-------|
| **t3.medium (On-Demand)** | 2 vCPU, 4GB RAM | ~$30/mo | Simple, no commitment |
| **t3.medium (Reserved 1yr)** | 2 vCPU, 4GB RAM | ~$19/mo | 37% savings, 1-year commitment |
| **t3.medium (Spot)** | 2 vCPU, 4GB RAM | ~$9-12/mo | Cheapest, but can be interrupted |
| **t3.small** | 2 vCPU, 2GB RAM | ~$15/mo | Tight on RAM — may swap with both models loaded |
| **t3.large** | 2 vCPU, 8GB RAM | ~$60/mo | Overkill unless traffic is high |

**Additional costs:**
- **EBS storage** (30GB gp3): ~$2.40/mo — for OS, code, ChromaDB vectorstore, model cache
- **Data transfer** (first 100GB/mo free, then $0.09/GB): likely negligible for a chatbot
- **Elastic IP** (if instance is running): free while attached

**Estimated total: ~$32/mo on-demand, ~$21/mo reserved**

## Architecture

```
Internet
  │
  ├─ Security Group (ports 80, 443, 22)
  │
  └─ EC2 (t3.medium, Ubuntu 22.04)
       ├─ Nginx (reverse proxy, port 80 → 8000)
       ├─ FastAPI / Uvicorn (port 8000)
       │    ├─ CrisisDetector (suicidal-electra, loaded in memory)
       │    ├─ ChromaDB (persistent on EBS, all-MiniLM-L6-v2 embeddings)
       │    └─ LLMHandler (calls Gemini API)
       └─ EBS Volume (30GB gp3)
            ├─ Application code
            ├─ ChromaDB vectorstore (data/processed/vectorstore/)
            └─ HuggingFace model cache (~500MB)
```

## What Runs Where

| Component | Runs On | Details |
|-----------|---------|---------|
| FastAPI server | EC2 | Long-running process via systemd |
| Crisis detection (ELECTRA) | EC2 (CPU) | Loaded once at startup, stays in memory |
| Embedding model (MiniLM) | EC2 (CPU) | Used by ChromaDB for query embedding |
| ChromaDB vector store | EC2 (EBS disk) | Persistent storage, ~50MB for current docs |
| LLM generation | Google Cloud | Gemini API call — not on EC2 |
| Conversation history | EC2 (in-memory) | Per-session, max 10 turns |

## Security Group Rules

| Type | Port | Source | Purpose |
|------|------|--------|---------|
| SSH | 22 | Your IP only | Admin access |
| HTTP | 80 | 0.0.0.0/0 | API access (Nginx → Uvicorn) |
| HTTPS | 443 | 0.0.0.0/0 | API access (if using SSL) |

## Setup Steps (High Level)

1. Launch `t3.medium` with Ubuntu 22.04 AMI
2. Attach 30GB gp3 EBS volume
3. Configure security group (ports 22, 80, 443)
4. SSH in, clone repo, install dependencies
5. Set `GOOGLE_API_KEY` in `.env`
6. Run FastAPI via systemd (auto-restart on crash/reboot)
7. Nginx reverse proxy in front (port 80 → 8000)
8. First startup downloads models (~500MB total), subsequent starts are fast

## Comparison vs Lambda (Current)

| Factor | Lambda | EC2 |
|--------|--------|-----|
| Cold start | 10-30s (model loading) | None (always running) |
| Cost (low traffic) | ~$5-10/mo | ~$32/mo |
| Cost (steady traffic) | Can spike with invocations | Fixed ~$32/mo |
| Conversation history | Lost between calls | Maintained in memory |
| ChromaDB persistence | Ephemeral `/tmp` | Persistent EBS |
| Complexity | Higher (stateless workarounds) | Lower (standard server) |
| Scaling | Auto-scales | Manual (or use ASG) |

**Recommendation:** EC2 `t3.medium` on-demand for development/demo, switch to reserved instance if keeping it running long-term.
