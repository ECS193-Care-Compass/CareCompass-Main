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


### Step 0: Create Your .env File


Copy the provided `.env.template` file to `.env` in the project root:

**macOS/Linux:**
```bash
cp .env.template .env
```

**Windows (CMD):**
```cmd
copy .env.template .env
```

**Windows (PowerShell):**
```powershell
Copy-Item .env.template .env
```

Then fill in the values for your environment. **See the comments in `.env.template` and the explanations below for each variable.**


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


### Example: Key Variables (see `.env.template` for full list)

```env
# GCP (Google Cloud Platform)
GCP_PROJECT_ID=your-gcp-project-id
GCP_REGION=us-central1
GCP_SERVICE_ACCOUNT_JSON=./gcp-key.json

# AWS
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-s3-bucket

# Vertex AI / Model
VERTEX_MODEL_NAME=gemini-pro
VERTEX_LOCATION=us-central1

# Lambda / Serverless
LAMBDA_FUNCTION_NAME=your-lambda-fn
LAMBDA_ROLE_ARN=your-lambda-role-arn

# Cache
DYNAMODB_TABLE_NAME=care-compass-response-cache-dev
CACHE_TTL_SECONDS=3600

# Deployment
ENVIRONMENT=dev

See the `.env.template` file for all available variables and copy it as your starting point.

For local development, you can use `gcloud auth application-default login` instead of a service account key.

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
MAX_OUTPUT_TOKENS=2048
EMBEDDING_MODEL=gemini-embedding-001
ENABLE_CRISIS_DETECTION=true
DYNAMODB_TABLE_NAME=care-compass-conversations
DYNAMODB_TTL_MINUTES=30
MAX_HISTORY_TURNS=5
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


## Response Caching & Privacy

CARE Bot uses a two-tier semantic response cache to reduce LLM costs and improve speed for common queries, while strictly protecting user privacy:

- **L1 (in-memory):** Fast, local cache (evicted on restart)
- **L2 (DynamoDB):** Persistent, shared cache (survives restarts, shared across instances)

**Privacy Guarantee:**
- Only the 3 preset button queries from the frontend are ever cached:
	- "Mental Health Support"
	- "Practical Needs Help"
	- "Legal & Advocacy Help"
- All other (free-form) user queries are NEVER cached or stored, even if they are similar to a preset.
- No raw user input, names, or sensitive information is ever written to DynamoDB or the cache.

**How it works:**
- When a user clicks a preset button, the canonical query string is used as the cache key.
- If a cache hit occurs, the response is returned instantly.
- All other queries always go to the LLM pipeline and are never cached.

**Configuring Cache TTLs:**
Set these in your `.env` (defaults shown):

```env
RESPONSE_CACHE_TTL=3600                # 1 hour for regular queries (not used by default)
RESPONSE_CACHE_FEATURED_TTL=604800     # 7 days for preset button queries
```

## Troubleshooting
| Problem | Fix |
|---------|-----|
| Cache not working | Check AWS credentials and DynamoDB table name in `.env` |
| Cache HIT not seen for preset | Ensure query matches preset exactly (case-insensitive, no extra words) |
| Privacy concern | Only preset queries are cached; all other input is never stored |
| Backend won't start | Check if port 8000 is already in use |
| Backend hangs on import | You're likely using Python 3.13. Delete venv and recreate with Python 3.12 |
| Slow first startup | Vectorstore is building via Gemini embedding API — wait for it to finish |
| Frontend can't reach backend | Make sure backend is running: `curl http://localhost:8000/health` |
| Sign up "Failed to fetch" | Check Supabase env vars in `chatbot-frontend/.env` and CSP in `src/main/index.ts` |
| DynamoDB unavailable | Check AWS credentials in `.env` — falls back to in-memory history gracefully |
| 429 Quota Exceeded | You've hit Vertex AI rate limits. Wait a moment and retry |
| Vertex AI auth error | Check `GOOGLE_APPLICATION_CREDENTIALS` path and service account permissions |
| GCP project mismatch | Ensure `GCP_PROJECT_ID` in `.env` matches the project ID in `gcp-key.json` |