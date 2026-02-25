# CARE Bot - Trauma-Informed RAG Chatbot

A trauma-informed chatbot powered by vector embeddings, semantic search, and Google Gemini AI. Built with FastAPI (backend), React + Electron (frontend), and ChromaDB (vector store).

## Quick Start

### Prerequisites

- **Python 3.12+**
- **Node.js 18+**
- **AWS Account** (for S3 storage and Lambda deployment)
- **Google Gemini API Key** (get one at [https://ai.google.dev](https://ai.google.dev))

### 1. Clone & Setup Backend

```bash
cd CareCompass

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory:

```env
# Google AI API
GOOGLE_API_KEY=your_gemini_api_key_here

# AWS S3 Buckets (created automatically, or provide your own)
S3_DOCUMENTS_BUCKET=care-compass-documents-{account-id}-dev
S3_PROCESSED_BUCKET=care-compass-processed-{account-id}-dev
S3_VECTORDB_BUCKET=care-compass-vectordb-{account-id}-dev
S3_LOGS_BUCKET=care-compass-logs-{account-id}-dev

# Model Configuration (optional)
MODEL_NAME=gemini-2.5-flash
TEMPERATURE=0.7
TOP_K=3
```

### 3. Run Backend

```bash
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
    [Crisis      [Retrieval] [Embedding] [LLM]
     Detector]   (ChromaDB)  (Sentence  (Gemini
                            Transformers) API)
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

### Chat
**POST** `/chat`
```json
{
  "query": "What STI testing do I need?",
  "scenario": "medical_followup"
}
```

### Categories
**GET** `/categories`  
Returns available support categories (medical, mental health, legal, etc.)

### Health Check
**GET** `/health`  
Returns `{"status": "ok"}`

### Stats
**GET** `/stats`  
Returns bot statistics (documents indexed, model info, etc.)

### Clear Conversation
**POST** `/clear`  
Clears conversation history for fresh start

## S3 Bucket Structure

Your system uses 4 dedicated S3 buckets:

| Bucket | Purpose | Contents |
|--------|---------|----------|
| **Documents** | Raw healthcare PDFs | SAMHSA guides, protocols, reference materials |
| **VectorDB** | Database backups | Weekly snapshots of ChromaDB (disaster recovery) |
| **Logs** | Audit trail | All API interactions with timestamps |
| **Processed** | (Reserved) | Future: processed documents for archival |

**Automatic Backups:** ChromaDB is backed up to S3 weekly (configurable in `api.py` line 101: `backup_interval_hours=168`)

## Core Components

### 1. Crisis Detection (`src/safety/crisis_detector.py`)
Scans for crisis keywords and provides immediate resources

### 2. Vector Store (`src/embeddings/vector_store.py`)
Local ChromaDB for fast semantic search (~300ms)

### 3. Retriever (`src/retrieval/retriever.py`)
Finds top-k relevant documents using cosine similarity

### 4. LLM Handler (`src/generation/llm_handler.py`)
Interface with Google Gemini API for response generation

### 5. Backup Scheduler (`src/utils/backup_scheduler.py`)
Automatic weekly backups of vector database to S3

## Configuration

Edit `config/settings.py` to customize:

```python
CHUNK_SIZE = 500              # Document chunk size (tokens)
CHUNK_OVERLAP = 50            # Overlap between chunks
TOP_K = 3                     # Documents to retrieve
SIMILARITY_THRESHOLD = 0.7    # Minimum similarity score
TEMPERATURE = 0.7             # LLM creativity (0-1)
```

## Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is in use
lsof -i :8000          # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill and restart
pkill -f uvicorn       # macOS/Linux
taskkill /IM python.exe  # Windows
```

### Vector store initialization slow
First startup downloads the embedding model (~400MB). Subsequent starts are fast.

### S3 upload errors
Verify AWS credentials: `~/.aws/credentials`  
Ensure bucket names match your account ID in `.env`

### Frontend can't reach backend
Check backend is running: `curl http://localhost:8000/health`  
Verify CORS is enabled (should be by default)

## Testing

```bash
# Test backup functionality
python test_backup.py

# Manual API test
curl http://localhost:8000/health
```

## Team Deployment Checklist

- [ ] Fork/clone repository
- [ ] Create `.env` file with API keys
- [ ] Run `pip install -r requirements.txt`
- [ ] Start backend: `uvicorn api:app --port 8000`
- [ ] Start frontend: `npm run dev`
- [ ] Test at `http://localhost:5173`
- [ ] Verify S3 backups in AWS console
- [ ] Create branch for your changes
- [ ] Push to main when ready

## Key Features

**Trauma-Informed:** Responses follow SAMHSA principles  
**Fast Retrieval:** Local vector search (~300ms)  
**Crisis Detection:** Immediate escalation when needed  
**Auto-Backup:** Weekly database backups to AWS S3  
**Audit Trail:** All interactions logged  
**Multi-Scenario:** Tailored responses for different situations  

## Environment Setup Details

### AWS Credentials
```bash
# Configure AWS credentials
aws configure

# Or manually create ~/.aws/credentials:
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
region = us-east-1
```

### First Run
The backend will:
1. Download embedding model (~400MB, first time only)
2. Initialize ChromaDB vector store
3. Begin accepting requests

## Support

For issues, check:
1. Backend logs: `http://localhost:8000/docs` (Swagger UI)
2. Browser console for frontend errors
3. S3 console for backup status
4. Ensure all environment variables are set
