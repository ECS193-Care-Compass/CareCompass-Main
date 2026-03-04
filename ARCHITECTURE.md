# CARE Bot System Architecture

## Component Details

### 1. Crisis Detector (`backend/src/safety/crisis_detector.py`)
**Purpose**: Two-layer detection of suicidal ideation and self-harm

```
User Input → Layer 1: Keyword Match → Layer 2: ML Model → Combined Result
                  ↓                         ↓                    ↓
           "kill myself"           gooohjy/suicidal-electra   is_crisis =
           "hurt myself"           LABEL_1 = suicidal          keyword OR
           "no hope"               LABEL_0 = non-suicidal      model triggered
```

A message is flagged as crisis if **either** layer triggers.

**Layer 1 — Keywords**: Fast substring matching against `CRISIS_KEYWORDS` list. No model load needed.
**Layer 2 — ML Model**: `gooohjy/suicidal-electra` (ELECTRA-based binary classifier). Lazy-loaded on first call; optional `warmup()` for eager loading at startup.

**Methods**:
- `analyze()`: Run both layers, return `{is_crisis, keyword_triggered, model_triggered, model_label}`
- `warmup()`: Force model load at startup to avoid first-request latency

### 2. Document Processor (`backend/src/embeddings/document_processor.py`)
**Purpose**: Convert PDFs into searchable chunks

```
PDF File → Extract Pages → Split into Chunks → Generate Embeddings
  ↓            ↓                ↓                      ↓
SAMHSA.pdf  Page 1-27     500 tokens/chunk      384-dim vectors
            Metadata      50 token overlap       (all-MiniLM-L6-v2)
```

**Methods**:
- `extract_text_from_pdf()`: Parse PDF pages
- `chunk_documents()`: Split into manageable pieces
- `generate_embeddings()`: Create vector representations

### 3. Vector Store (`backend/src/embeddings/vector_store.py`)
**Purpose**: Persistent storage and fast similarity search

**Technology**: ChromaDB
- Persistent storage in `data/processed/vectorstore/`
- Cosine similarity search
- Metadata filtering support

**Key Methods**:
- `add_documents()`: Store embeddings
- `similarity_search()`: Find top-k matches
- `similarity_search_with_score()`: Filter by threshold

### 4. Retriever (`backend/src/retrieval/retriever.py`)
**Purpose**: Find relevant context for user queries

```
Query → Embed → Search Vector Store → Filter Results → Return Top-K
  ↓       ↓           ↓                     ↓              ↓
"STI    384-dim   Cosine           Distance < 0.7    Top 3 docs
test"   vector    similarity       threshold         with metadata
```

**Methods**:
- `retrieve()`: Standard retrieval
- `retrieve_by_scenario()`: Filter by category
- `format_context_for_prompt()`: Prepare for LLM

### 5. Prompt Templates (`backend/src/generation/prompt_templates.py`)
**Purpose**: Construct trauma-informed prompts

**Methods**:
- `get_system_prompt()`: Base trauma-informed instructions
- `get_rag_prompt()`: Complete RAG prompt
- `get_scenario_specific_prompt()`: Tailored for scenarios

### 6. LLM Handler — Google Gemini (`backend/src/generation/llm_handler.py`)
**Purpose**: Interface with Google Gemini API (default provider)

**Configuration**:
```
Model: gemini-2.5-flash (configurable via MODEL_NAME)
Temperature: 0.7 (balanced creativity/consistency)
Max Tokens: 4096
Conversation History: 10 turns max
```

**Methods**:
- `generate_response()`: Call Gemini API with optional crisis instruction injection
- `test_connection()`: Verify API access
- `clear_history()`: Reset conversation history
- `get_history_summary()`: Return turn count and message stats

### 7. Ollama Handler (`backend/src/generation/ollama_handler.py`)
**Purpose**: On-device LLM inference via Ollama (all data stays local)

Drop-in alternative to LLMHandler. Selected when `LLM_PROVIDER=ollama` in environment.

**Configuration**:
```
Model: llama3.1 (configurable via OLLAMA_MODEL)
Base URL: http://localhost:11434 (configurable via OLLAMA_BASE_URL)
Conversation History: 10 turns max
```

**Methods**: Same interface as LLMHandler — `generate_response()`, `clear_history()`, `get_history_summary()`, `test_connection()`

### LLM Provider Selection (`backend/main.py`)
```python
if LLM_PROVIDER == "ollama":
    self.llm_handler = OllamaHandler()
else:
    self.llm_handler = LLMHandler()  # Google Gemini (default)
```

Set `LLM_PROVIDER` in `.env`:
- `gemini` (default) — requires `GOOGLE_API_KEY`
- `ollama` — requires local Ollama running, configurable via `OLLAMA_MODEL` and `OLLAMA_BASE_URL`

## Data Flow Example

### Example: "What STI testing do I need?"

1. **Input Processing**
```
User Query: "What STI testing do I need?"
↓
Crisis Check (two-layer):
  Layer 1 — Keywords: [No match]
  Layer 2 — ML Model: LABEL_0 (non-suicidal)
  Result: is_crisis = false
↓
Continue to retrieval...
```

2. **Retrieval**
```
Query Embedding: [0.234, -0.123, 0.456, ...]
↓
Vector Search: Find similar chunks
↓
Results:
  1. "Repeat STI testing recommended at 2 weeks..." (SAMHSA, p.8)
  2. "Follow-up appointments include STI screening..." (Proposal, p.2)
  3. "Testing timeline varies by infection type..." (SAMHSA, p.12)
```

3. **Prompt Construction**
```
System Prompt: [Trauma-informed principles]
+
Context: [3 retrieved documents]
+
Query: "What STI testing do I need?"
+
Instructions: [How to respond]
```

4. **Generation**
```
LLM Call (Gemini or Ollama depending on LLM_PROVIDER)
↓
Response: "I understand you're looking for information about
STI testing after your exam. It's completely your choice what
testing you pursue, and I'm here to help you understand the
recommendations. Based on medical guidelines, testing is
typically recommended at..."
```

5. **Output**
```
Final Response: [Empathetic, informative, choice-focused]
Metadata: {
  crisis: false,
  keyword_triggered: false,
  model_triggered: false,
  docs_retrieved: 3,
  sources: ["SAMHSA", "Proposal"]
}
```

## Configuration Files

### `backend/config/settings.py`
- `BACKEND_DIR` / `PROJECT_ROOT` — path resolution
- `DATA_DIR`, `RAW_DATA_DIR`, `VECTORSTORE_DIR` — data paths (at project root)
- `GOOGLE_API_KEY` — Gemini API key
- `EMBEDDING_MODEL` — sentence-transformers model (default: `all-MiniLM-L6-v2`)
- `CHUNK_SIZE` (500), `CHUNK_OVERLAP` (50) — document chunking
- `TOP_K` (3), `SIMILARITY_THRESHOLD` (0.7) — retrieval tuning
- `LLM_PROVIDER` — `"gemini"` or `"ollama"`
- `MODEL_NAME` (gemini-2.5-flash), `TEMPERATURE` (0.7), `MAX_OUTPUT_TOKENS` (4096)
- `OLLAMA_MODEL` (llama3.1), `OLLAMA_BASE_URL` (http://localhost:11434)
- `ENABLE_CRISIS_DETECTION` — toggle crisis detection on/off

### `backend/config/trauma_informed_principles.py`
- Six key principles
- The Four R's
- Scenario categories
- Crisis keywords
- Referral categories

## Extension Points

### Adding New Scenarios
1. Add to `SCENARIO_CATEGORIES` in `backend/config/trauma_informed_principles.py`
2. Create scenario-specific prompt in `backend/src/generation/prompt_templates.py`
3. Add test queries to `sample_queries.json`

### Adding New Documents
1. Place PDF in `data/raw/`
2. Update `backend/src/embeddings/document_processor.py` if custom processing needed
3. Rebuild vector store with `force_rebuild=True`

### Customizing Retrieval
1. Adjust `TOP_K` in `backend/config/settings.py`
2. Modify `CHUNK_SIZE` and `CHUNK_OVERLAP`
3. Implement reranking in `backend/src/retrieval/retriever.py`

### Enhancing Safety
1. Add keywords to `CRISIS_KEYWORDS` in `backend/src/safety/crisis_detector.py`
2. Adjust ML model threshold or swap model ID
3. Update crisis instruction template in `LLMHandler._inject_crisis_instruction()`

### Switching LLM Provider
1. Set `LLM_PROVIDER=ollama` in `.env`
2. Install and start Ollama: `ollama serve`
3. Pull a model: `ollama pull llama3.1`
4. Optionally set `OLLAMA_MODEL` and `OLLAMA_BASE_URL` in `.env`

## Monitoring & Logging

All components log to:
- Console: INFO level
- File: DEBUG level (in `logs/`)