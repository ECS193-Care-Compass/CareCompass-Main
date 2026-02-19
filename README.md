# CARE Bot - Trauma-Informed Support Chatbot

## Architecture


```
User Query
    ↓
[Crisis Detection] ← Immediate escalation if needed
    ↓
[Query Embedding]
    ↓
[Vector Search] ← ChromaDB with semantic similarity
    ↓
[Document Retrieval] ← Top-k relevant chunks
    ↓
[Prompt Construction] ← System prompt + context + query
    ↓
[Gemini API] ← Generate trauma-informed response
    ↓
Response to User
```

## Installation

### Setup

1. **Go to directory**
```bash
cd care-bot
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
./script.sh
```

4. **Set up environment variables**

To get a Google API key:
- Create a new API key
- Copy it to your `.env` file

add your Google API key:
```
GOOGLE_API_KEY=your_actual_api_key_here
```

5. **Add documents to process**

Place your PDF documents in `data/raw/`:
- `SAMHSA_Trauma-2014__1_.pdf`
- Add additional scenario documents, referral guides, etc.

## Usage

### Quick Start


Backend:
```bash

```
Frontend:
```bash
npm run dev
```

This will:
1. Initialize the vector store (first run only)
2. Process documents and create embeddings
3. Start an interactive chat session

### Configuration

Adjust settings in `config/settings.py` or via environment variables:

- `TOP_K`: Number of documents to retrieve (default: 3)
- `TEMPERATURE`: LLM temperature (default: 0.7)
- `CHUNK_SIZE`: Document chunk size (default: 500)
- `SIMILARITY_THRESHOLD`: Minimum similarity score (default: 0.7)

## Project Structure

```
care-bot/
├── README.md
├── requirements.txt
├── .env.example
├── main.py                          # Main application entry point
│
├── config/
│   ├── settings.py                  # Configuration settings
│   └── trauma_informed_principles.py # SAMHSA principles & constants
│
├── src/
│   ├── embeddings/
│   │   ├── document_processor.py    # PDF processing & chunking
│   │   └── vector_store.py          # ChromaDB management
│   │
│   ├── retrieval/
│   │   └── retriever.py             # Semantic search & retrieval
│   │
│   ├── generation/
│   │   ├── prompt_templates.py      # Trauma-informed prompts
│   │   └── llm_handler.py           # Gemini API interface
│   │
│   ├── safety/
│   │   └── crisis_detector.py       # Crisis detection & response
│   │
│   └── utils/
│       └── logger.py                # Logging utilities
│
├── data/
│   ├── raw/                         # Source documents (PDFs)
│   └── processed/
│       └── vectorstore/             # ChromaDB persistent storage
│
├── logs/                            # Application logs
│
└── tests/                           # Unit tests
```

## Customization

### Adding New Documents

1. Place PDF in `data/raw/`
2. Update `document_processor.py` to include new source
3. Rebuild vector store:

```python
bot = CAREBot()
bot.initialize_vector_store(force_rebuild=True)
```

### Modifying Retrieval

Adjust parameters in `config/settings.py`:

```python
TOP_K = 5  # Retrieve more documents
CHUNK_SIZE = 1000  # Larger chunks
CHUNK_OVERLAP = 100  # More overlap between chunks
```

### Customizing Prompts

Edit templates in `src/generation/prompt_templates.py`:

```python
class PromptTemplates:
    @staticmethod
    def get_system_prompt() -> str:
        # Modify the base system prompt
        return """Your custom system prompt..."""
```

### Adding Scenario Categories

Update `config/trauma_informed_principles.py`:

```python
SCENARIO_CATEGORIES = {
    "your_new_category": {
        "name": "Category Name",
        "description": "Description",
        "priority": "high"
    }
}
```

## Testing

Run tests:

```bash
pytest tests/
```

Test individual components:

```bash
# Test document processing
python src/embeddings/document_processor.py

# Test vector store
python src/embeddings/vector_store.py

# Test retrieval
python src/retrieval/retriever.py

# Test crisis detection
python src/safety/crisis_detector.py
```