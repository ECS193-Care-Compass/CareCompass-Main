# CARE Bot - Trauma-Informed RAG Chatbot

## Prerequisites

- **Python 3.12+**
- **Node.js 18+**
- **Google Gemini API Key** — get one at [https://ai.google.dev](https://ai.google.dev)

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
GOOGLE_API_KEY=your_gemini_api_key_here
```

Optional settings (defaults shown):

```env
MODEL_NAME=gemini-2.5-flash
TEMPERATURE=0.7
TOP_K=3
SIMILARITY_THRESHOLD=0.7
MAX_OUTPUT_TOKENS=4096
EMBEDDING_MODEL=all-MiniLM-L6-v2
ENABLE_CRISIS_DETECTION=true
```

## 3. Run Backend

```bash
cd backend

# Development (auto-reload)
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

Backend ready at: `http://localhost:8000`

> First startup downloads the embedding model (~400MB). Subsequent starts are fast.

## 4. Run Frontend

```bash
cd chatbot-frontend

# Install dependencies
npm install

# Development
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

## Run Tests

```bash
cd backend
python -m pytest tests/
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Backend won't start | Check if port 8000 is already in use |
| Slow first startup | Embedding model is downloading (~400MB) — wait for it to finish |
| Frontend can't reach backend | Make sure backend is running: `curl http://localhost:8000/health` |
