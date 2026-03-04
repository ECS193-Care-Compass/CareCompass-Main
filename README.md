# CARE Bot - Trauma-Informed RAG Chatbot

A trauma-informed chatbot powered by vector embeddings, semantic search, and LLM generation. Built with FastAPI (backend), React + Electron (frontend), and ChromaDB (vector store). Supports Google Gemini API or local Ollama inference.

## Quick Start

### Prerequisites

- **Python 3.12+**
- **Node.js 18+**
- **Google Gemini API Key** (get one at [https://ai.google.dev](https://ai.google.dev)) — or **Ollama** for on-device inference
- **AWS Account** (optional, for S3 storage and Lambda deployment)

### 1. Clone & Setup Backend

```bash
cd CareCompass/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the **project root** (not inside `backend/`):

```env
# LLM Provider — "gemini" (default) or "ollama"
LLM_PROVIDER=gemini

# Google Gemini (required when LLM_PROVIDER=gemini)
GOOGLE_API_KEY=your_gemini_api_key_here
MODEL_NAME=gemini-2.5-flash

# Ollama (used when LLM_PROVIDER=ollama)
OLLAMA_MODEL=llama3.1
OLLAMA_BASE_URL=http://localhost:11434

# Model Configuration (optional)
TEMPERATURE=0.7
TOP_K=3
SIMILARITY_THRESHOLD=0.7
MAX_OUTPUT_TOKENS=4096
EMBEDDING_MODEL=all-MiniLM-L6-v2
ENABLE_CRISIS_DETECTION=true

# AWS S3 Buckets (optional, for backups and logging)
S3_DOCUMENTS_BUCKET=care-compass-documents-{account-id}-dev
S3_VECTORDB_BUCKET=care-compass-vectordb-{account-id}-dev
S3_LOGS_BUCKET=care-compass-logs-{account-id}-dev
```

### 3. Run Backend

```bash
cd backend

# Development with auto-reload
uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# Production (no reload)
uvicorn api:app --host 0.0.0.0 --port 8000
```

Backend ready at: `http://localhost:8000`
API docs: `http://localhost:8000/docs`

### 4. Run Frontend

```bash
cd chatbot-frontend

# Install dependencies
npm install

# Development
npm run dev

# Build for production
npm run build
```

Frontend ready at: `http://localhost:5173`

## Using Ollama (On-Device LLM)

All user data stays local — nothing is sent to an external API.

### Windows
1. **Install Ollama** — download from [ollama.com](https://ollama.com)
2. **Pull a model**: `ollama pull llama3.1`
3. Ollama runs automatically in the background after install.

### WSL (recommended for development)
1. **Install dependencies and Ollama**:
   ```bash
   sudo apt-get install zstd -y
   curl -fsSL https://ollama.com/install.sh | sh
   ```
2. **Pull a model**: `ollama pull llama3.1`
3. **Start Ollama**:
   ```bash
   ollama serve
   ```

> **Note:** Install Ollama inside WSL (not the Windows app) so the backend can reach it on `localhost`. WSL2 automatically passes through NVIDIA GPU access — verify with `nvidia-smi`.

### Configuration
Set your root `.env`:
```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.1
```
Start the backend as usual — the provider switch is automatic.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Electron + React App                  │
└─────────────────────────────────────────────────────────┘
                            ↓
                    FastAPI Backend (8000)
                            ↓
            ┌───────────────────────────────┐
            ↓           ↓          ↓         ↓
    [Crisis      [Retrieval] [Embedding] [LLM Provider]
     Detector]   (ChromaDB)  (Sentence    Gemini API
     Keywords +              Transformers)  — or —
     ML Model                             Ollama (local)
            ↓           ↓          ↓         ↓
            └───────────────────────────────┘
                            ↓
            ┌──────────────────────┐
            ↓           ↓          ↓
        [Documents] [Logs]    [VectorDB]
         (S3)       (S3)       (S3)
        Raw PDFs   API Calls  Backups
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/chat` | Send query (+ optional scenario), get response |
| POST | `/clear` | Reset conversation history |
| GET | `/health` | Health check |
| GET | `/stats` | Bot statistics |
| GET | `/categories` | Available scenario categories |

### Chat Example
**POST** `/chat`
```json
{
  "query": "What STI testing do I need?",
  "scenario": "immediate_followup"
}
```

Response:
```json
{
  "response": "...",
  "is_crisis": false,
  "num_docs_retrieved": 3,
  "scenario": "immediate_followup",
  "blocked": false
}
```

## Core Components

### 1. Crisis Detection (`backend/src/safety/crisis_detector.py`)
Two-layer detection of suicidal ideation and self-harm:
- **Layer 1** — Keyword matching (fast, no model needed)
- **Layer 2** — ML model (`gooohjy/suicidal-electra`, ELECTRA-based binary classifier)

A message is flagged if **either** layer triggers. Crisis detection runs **before** retrieval.

### 2. Vector Store (`backend/src/embeddings/vector_store.py`)
Local ChromaDB for fast semantic search

### 3. Retriever (`backend/src/retrieval/retriever.py`)
Finds top-k relevant documents using cosine similarity

### 4. LLM Handlers (`backend/src/generation/`)
- `llm_handler.py` — Google Gemini API (default)
- `ollama_handler.py` — Local Ollama inference (on-device)

Selected automatically based on `LLM_PROVIDER` env var.

### 5. Backup Scheduler (`backend/src/utils/backup_scheduler.py`)
Automatic weekly backups of vector database to S3

## Configuration

Edit `backend/config/settings.py` to customize:

```python
CHUNK_SIZE = 500              # Document chunk size (tokens)
CHUNK_OVERLAP = 50            # Overlap between chunks
TOP_K = 3                     # Documents to retrieve
SIMILARITY_THRESHOLD = 0.7    # Minimum similarity score
TEMPERATURE = 0.7             # LLM creativity (0-1)
MAX_OUTPUT_TOKENS = 4096      # Max response length
```

## Testing

```bash
cd backend

# Run all tests
python -m pytest tests/

# Individual test files
python tests/test_rag.py
python tests/test_scenarios.py
python tests/test_backup.py
```

## S3 Bucket Structure

| Bucket | Purpose | Contents |
|--------|---------|----------|
| **Documents** | Raw healthcare PDFs | SAMHSA guides, protocols, reference materials |
| **VectorDB** | Database backups | Weekly snapshots of ChromaDB (disaster recovery) |
| **Logs** | Audit trail | All API interactions with timestamps |

## Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is in use
lsof -i :8000          # macOS/Linux
netstat -ano | findstr :8000  # Windows
```

### Vector store initialization slow
First startup downloads the embedding model (~400MB). Subsequent starts are fast.

### Ollama connection errors
Make sure Ollama is running (`ollama serve`) and the model is pulled (`ollama pull llama3.1`).

### Frontend can't reach backend
Check backend is running: `curl http://localhost:8000/health`

### S3 upload errors
Verify AWS credentials: `~/.aws/credentials`
Ensure bucket names match your account ID in `.env`

## AWS Deployment

```bash
# Windows
./aws/deployment/deploy.ps1 -Environment dev -GoogleApiKey "your_key"

# Mac/Linux
./aws/deployment/deploy.sh -e dev -k "your_key"
```

## Key Features

**Trauma-Informed:** Responses follow SAMHSA's six principles
**Dual LLM Support:** Google Gemini API or local Ollama (privacy-first)
**Two-Layer Crisis Detection:** Keywords + ML model for reliable safety
**Fast Retrieval:** Local vector search with ChromaDB
**Auto-Backup:** Weekly database backups to AWS S3
**Audit Trail:** All interactions logged
**Multi-Scenario:** Tailored responses for different support categories