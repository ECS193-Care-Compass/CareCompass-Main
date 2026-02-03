# CARE Bot System Architecture

## Component Details

### 1. Crisis Detector (`src/safety/crisis_detector.py`)
**Purpose**: Identify users in distress and provide immediate support

```
User Input → Keyword Matching → Severity Assessment → Response Selection
                ↓                       ↓                    ↓
         "suicide"              [critical]           988 Hotline
         "hurt myself"          [high]               Crisis Resources
         "no hope"              [moderate]           Support Info
```

**Methods**:
- `detect_crisis()`: Scan text for indicators
- `assess_severity()`: Rate crisis level (none/moderate/high/critical)
- `get_crisis_response()`: Return appropriate immediate response

### 2. Document Processor (`src/embeddings/document_processor.py`)
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

### 3. Vector Store (`src/embeddings/vector_store.py`)
**Purpose**: Persistent storage and fast similarity search

**Technology**: ChromaDB
- Persistent storage in `data/processed/vectorstore/`
- Cosine similarity search
- Metadata filtering support

**Key Methods**:
- `add_documents()`: Store embeddings
- `similarity_search()`: Find top-k matches
- `similarity_search_with_score()`: Filter by threshold

### 4. Retriever (`src/retrieval/retriever.py`)
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

### 5. Prompt Templates (`src/generation/prompt_templates.py`)
**Purpose**: Construct trauma-informed prompts

**Methods**:
- `get_system_prompt()`: Base trauma-informed instructions
- `get_rag_prompt()`: Complete RAG prompt
- `get_scenario_specific_prompt()`: Tailored for scenarios

### 6. LLM Handler (`src/generation/llm_handler.py`)
**Purpose**: Interface with Google Gemini API

**Configuration**:
```
Model: gemini-pro
Temperature: 0.7 (balanced creativity/consistency)
Max Tokens: 1024
Safety Settings: Balanced for trauma context
```

**Methods**:
- `generate_response()`: Call Gemini API
- `test_connection()`: Verify API access
- Fallback responses for errors

## Data Flow Example

### Example: "What STI testing do I need?"

1. **Input Processing**
```
User Query: "What STI testing do I need?"
↓
Crisis Check: [No crisis detected]
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
Gemini API Call
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
  docs_retrieved: 3,
  sources: ["SAMHSA", "Proposal"]
}
```

## Configuration Files

### `config/settings.py`
- File paths
- API keys
- Model parameters
- Retrieval settings

### `config/trauma_informed_principles.py`
- Six key principles
- The Four R's
- Scenario categories
- Crisis keywords
- Referral categories

## Extension Points

### Adding New Scenarios
1. Add to `SCENARIO_CATEGORIES` in `trauma_informed_principles.py`
2. Create scenario-specific prompt in `prompt_templates.py`
3. Add test queries to `sample_queries.json`

### Adding New Documents
1. Place PDF in `data/raw/`
2. Update `document_processor.py` if custom processing needed
3. Rebuild vector store with `force_rebuild=True`

### Customizing Retrieval
1. Adjust `TOP_K` in `settings.py`
2. Modify `CHUNK_SIZE` and `CHUNK_OVERLAP`
3. Implement reranking in `retriever.py`

### Enhancing Safety
1. Add keywords to `CRISIS_INDICATORS`
2. Modify severity assessment logic
3. Update crisis response templates

## Monitoring & Logging

All components log to:
- Console: INFO level
- File: DEBUG level (in `logs/`)
