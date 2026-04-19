import os
from pathlib import Path
from dotenv import load_dotenv

# Base directories
BACKEND_DIR = Path(__file__).parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

# Load environment variables from project root 
if not os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    load_dotenv(PROJECT_ROOT / ".env")

# Data lives at project root
BASE_DIR = PROJECT_ROOT
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
VECTORSTORE_DIR = PROCESSED_DATA_DIR / "vectorstore"

# Create directories if they don't exist 
if not os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    for directory in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, VECTORSTORE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

# Vertex AI Configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")

# Embedding Configuration
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Retrieval Configuration
TOP_K = int(os.getenv("TOP_K", "3"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))

# LLM Configuration
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "4096"))

# Safety Configuration
ENABLE_CRISIS_DETECTION = os.getenv("ENABLE_CRISIS_DETECTION", "true").lower() == "true"

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

# DynamoDB Configuration
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "care-compass-conversations")
DYNAMODB_REGION = os.getenv("AWS_REGION", "us-east-1")
DYNAMODB_TTL_MINUTES = int(os.getenv("DYNAMODB_TTL_MINUTES", "30"))
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "10"))

# Document metadata fields to preserve
METADATA_FIELDS = [
    "source",
    "page",
    "category",
    "scenario_type",
    "trauma_principle"
]
