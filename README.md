# CARE Bot - Trauma-Informed RAG Chatbot

## Prerequisites

- **Python 3.12** (recommended) — **Do NOT use Python 3.13** (has known bugs with google-cloud-aiplatform SDK)
- **Node.js 18+**
- **Google Cloud Platform account**
- **Supabase project** 
- **AWS account**


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

Create a `.env` file in the **project root**.

### Step 1: Enable Vertex AI API

1. Go to [GCP Console](https://console.cloud.google.com/)
2. Select or create a project
3. Navigate to **APIs & Services** → **Enable APIs and Services**
4. Search for "Vertex AI API" and click **Enable**

### Step 2: Create a Service Account

1. Go to **IAM & Admin** → **Service Accounts**
2. Click **Create Service Account**
3. Name it (e.g., `care-compass-vertex`)
4. Grant the **Vertex AI User** role
5. Click **Done**

### Step 3: Generate a JSON Key

1. Click on the service account you just created
2. Go to the **Keys** tab
3. Click **Add Key** → **Create new key** → **JSON**
4. Save the downloaded file as `gcp-key.json` in the project root

### Step 4: Configure `.env`

```env
# Vertex AI (required)
GCP_PROJECT_ID=your-gcp-project-id
GCP_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=C:\full\path\to\CareCompass\gcp-key.json

# Supabase (authentication)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_JWT_SECRET=your_supabase_jwt_secret

# AWS (DynamoDB + S3)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
```

Instead of a service account key, you can authenticate with your personal Google account:

```bash
gcloud auth application-default login
```

This creates credentials at `~/.config/gcloud/application_default_credentials.json` that the SDK will use automatically. You still need to set `GCP_PROJECT_ID` in your `.env`.

### Optional Settings

Defaults shown:

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
# 3. Setup Frontend Environment

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
.\aws\deployment\deploy.ps1 -Environment dev -AWSProfile your_profile -GCPProjectId "your-project-id" -GCPKeyFile "C:\path\to\gcp-key.json" -SupabaseJwtSecret "your_secret"
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
| Backend hangs on import | You're likely using Python 3.13. Delete venv and recreate with Python 3.12 |
| Slow first startup | Vectorstore is building via Gemini embedding API — wait for it to finish |
| Frontend can't reach backend | Make sure backend is running: `curl http://localhost:8000/health` |
| Sign up "Failed to fetch" | Check Supabase env vars in `chatbot-frontend/.env` and CSP in `src/main/index.ts` |
| DynamoDB unavailable | Check AWS credentials in `.env` — falls back to in-memory history gracefully |
| 429 Quota Exceeded | You've hit Vertex AI rate limits. Wait a moment and retry |
| Vertex AI auth error | Check `GOOGLE_APPLICATION_CREDENTIALS` path and service account permissions |
| GCP project mismatch | Ensure `GCP_PROJECT_ID` in `.env` matches the project ID in `gcp-key.json` |