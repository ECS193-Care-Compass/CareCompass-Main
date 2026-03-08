# CARE Bot - Trauma-Informed RAG Chatbot

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Google Gemini API Key** — get one at [https://ai.google.dev](https://ai.google.dev)
- **Supabase project** (free tier) — for authentication
- **AWS account** — for DynamoDB (conversation history) and S3 (logs, vectorstore backup)

## 1. Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 2. Configure Environment

Create a `.env` file in the **project root**:

```env
# Required
GOOGLE_API_KEY=your_gemini_api_key_here

# Supabase (authentication)
SUPABASE_JWT_SECRET=your_supabase_jwt_secret

# AWS (DynamoDB + S3)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
```

Optional settings (defaults shown):

```env
MODEL_NAME=gemini-2.5-flash
TEMPERATURE=0.7
TOP_K=3
SIMILARITY_THRESHOLD=0.7
MAX_OUTPUT_TOKENS=4096
EMBEDDING_MODEL=gemini-embedding-001
ENABLE_CRISIS_DETECTION=true
DYNAMODB_TABLE_NAME=care-compass-conversations
DYNAMODB_TTL_MINUTES=30
MAX_HISTORY_TURNS=10
```

## 3. Setup Frontend Environment

Create a `.env` file in `chatbot-frontend/`:

```env
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

## 4. Run Backend

```bash
cd backend
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

Backend ready at: `http://localhost:8000`

> First startup builds the vectorstore using the Gemini embedding API. This may take a few minutes due to API rate limiting. Subsequent starts are fast.

## 5. Run Frontend

```bash
cd chatbot-frontend
npm install
npm run dev
```

Frontend ready at: `http://localhost:5173`

## Build Frontend for Desktop

```bash
cd chatbot-frontend
npm run build:win    # Windows
npm run build:mac    # macOS
npm run build:linux  # Linux
```

## Deploy to AWS Lambda

```powershell
# Windows (PowerShell) — requires AWS CLI v2
.\aws\deployment\deploy.ps1 -Environment dev -AWSProfile your_profile -GoogleApiKey "your_key" -SupabaseJwtSecret "your_secret"
```

Before deploying, upload the vectorstore to S3:
```bash
python aws/scripts/upload_vectorstore.py
```

See [aws/README.md](aws/README.md) for full deployment guide.

## Run Tests

```bash
cd backend
python -m pytest tests/
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Backend won't start | Check if port 8000 is already in use |
| Slow first startup | Vectorstore is building via Gemini embedding API — wait for it to finish |
| Frontend can't reach backend | Make sure backend is running: `curl http://localhost:8000/health` |
| Sign up "Failed to fetch" | Check Supabase env vars in `chatbot-frontend/.env` and CSP in `src/main/index.ts` |
| DynamoDB unavailable | Check AWS credentials in `.env` — falls back to in-memory history gracefully |