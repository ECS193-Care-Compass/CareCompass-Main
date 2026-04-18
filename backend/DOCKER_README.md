# CARE Bot Backend — Docker Setup

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop) installed and running
- A `.env` file at the project root with the required environment variables (see below)

---

## Environment Variables

Create a `.env` file at `/CareCompass/.env` with the following:

```env
# Required
GOOGLE_API_KEY=your_google_api_key_here

# AWS
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# DynamoDB (for persistent conversation history)
DYNAMODB_TABLE_NAME=care-compass-conversations
DYNAMODB_TTL_MINUTES=30
MAX_HISTORY_TURNS=10

# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_JWT_SECRET=your_supabase_jwt_secret

# Model settings (optional — defaults shown)
EMBEDDING_MODEL=gemini-embedding-001
MODEL_NAME=gemini-2.5-flash
TEMPERATURE=0.7
MAX_OUTPUT_TOKENS=4096
TOP_K=3
SIMILARITY_THRESHOLD=0.7
ENABLE_CRISIS_DETECTION=true
```

---

## Project Structure

```
CareCompass/
├── .env                        # Environment variables (never commit this)
├── data/
│   └── raw/                    # PDF documents for the RAG pipeline
│       ├── SAMHSA_Trauma-2014__1_.pdf
│       ├── sma14-4816.pdf
│       └── ...
└── backend/
    ├── Dockerfile
    ├── docker-compose.yml
    ├── requirements.txt
    ├── api.py
    ├── main.py
    ├── config/
    └── src/
```

---

## Building the Image

From the `backend/` directory:

```bash
cd CareCompass/backend
docker build -t carebot-backend .
```

This will:
- Pull Python 3.11 slim base image
- Install all dependencies from `requirements.txt`
- Copy the application source code into the container

---

## Running the Container

```bash
docker run -p 8000:8000 \
  --env-file /path/to/CareCompass/.env \
  -v /path/to/CareCompass/data:/data \
  carebot-backend
```

The `-v` flag mounts your local `data/` folder into the container so it can access the PDF documents and vectorstore.

### Using Docker Compose (recommended)

```bash
docker-compose up
```

To run in the background:
```bash
docker-compose up -d
```

To stop:
```bash
docker-compose down
```

---

## Testing the API

Once the container is running, test it with:

```bash
# Health check
curl http://localhost:8000/health

# Chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is trauma-informed care?", "session_id": "test-123"}'
```

A successful health check returns:
```json
{"status": "ok", "message": "CARE Bot API is running"}
```

---

## Known Warnings

### DynamoDB unavailable
```
DynamoDB unavailable, falling back to in-memory history
```
This means conversation history will not persist between sessions. To fix, ensure your AWS credentials in `.env` are valid and not expired.

### Backup scheduler failed
```
Could not start backup scheduler: 'NoneType' object is not callable
```
Non-blocking — does not affect core chat functionality.

### ChromaDB telemetry
```
Failed to send telemetry event
```
Non-blocking — ChromaDB attempting to send usage data. Does not affect functionality.

---

## Transferring to a New Machine

1. Make sure Docker Desktop is installed on the new machine
2. Clone the repository
3. Copy the `.env` file to the project root (never commit this to GitHub)
4. Copy the `data/` folder with all PDFs to the project root
5. Build and run:

```bash
cd backend
docker build -t carebot-backend .
docker run -p 8000:8000 \
  --env-file ../.env \
  -v ../data:/data \
  carebot-backend
```

---

## Pushing to Docker Hub (for account transfer)

Tag and push the image so the new owner can pull it directly:

```bash
# Tag the image
docker tag carebot-backend your-dockerhub-username/carebot-backend:latest

# Push to Docker Hub
docker push your-dockerhub-username/carebot-backend:latest
```

The new owner can then pull and run without building:
```bash
docker pull your-dockerhub-username/carebot-backend:latest
docker run -p 8000:8000 \
  --env-file .env \
  -v ./data:/data \
  your-dockerhub-username/carebot-backend:latest
```

---

## Frontend Configuration

After the backend is running locally, update the frontend `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

For production, point to your deployed backend URL:
```env
VITE_API_BASE_URL=https://your-api-gateway-url/dev
```
