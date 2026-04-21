"""
CARE Bot - Trauma-Informed RAG Chatbot
Main application orchestrating the RAG pipeline
"""
import os
from typing import Dict, Any, Optional
from src.embeddings.document_processor import DocumentProcessor
from src.embeddings.vector_store import VectorStore
from src.retrieval.retriever import Retriever
from src.generation.prompt_templates import PromptTemplates
from src.generation.llm_handler import LLMHandler
from src.safety.crisis_detector import CrisisDetector, CRISIS_KEYWORDS
from src.utils.logger import get_logger, log_interaction
from src.utils.response_cache import ResponseCache
from config.settings import (
    TOP_K, RESPONSE_CACHE_ENABLED, RESPONSE_CACHE_SIMILARITY,
    RESPONSE_CACHE_SIZE, RESPONSE_CACHE_TTL, RESPONSE_CACHE_FEATURED_TTL
)

logger = get_logger(__name__)

# Crisis emphasis prepended to prompt when keywords trigger
_CRISIS_EMPHASIS = """
=== CRISIS PROTOCOL — SUICIDAL IDEATION DETECTED ===
User has expressed suicidal thoughts or self-harm ideation.

Your response MUST:
1. Open with immediate, warm acknowledgment of their pain
2. Provide these crisis resources early in your response:
   - 988 Suicide & Crisis Lifeline — call or text 988 (free, 24/7)
   - Crisis Text Line — text HOME to 741741
3. Keep the tone calm, human, and not clinical
4. Answer their question while maintaining safety focus
5. End with a gentle invitation to keep talking

DO NOT include these resources in normal (non-crisis) conversations.
"""


class CAREBot:
    """Main CARE Bot application class"""

    def __init__(self, top_k: int = TOP_K):
        """
        Initialize CARE Bot with all components.

        Args:
            top_k: Number of documents to retrieve for context
        """
        logger.info("Initializing CARE Bot...")

        self.vector_store = VectorStore()
        self.retriever = Retriever(self.vector_store, top_k=top_k)

        self.llm_handler = LLMHandler()

        self.prompt_templates = PromptTemplates()

        self.initialize_vector_store(force_rebuild=False)

        # Keyword-only crisis detector (LLM handles implicit detection)
        self.crisis_detector = CrisisDetector()

        # Response cache for cost optimization
        if RESPONSE_CACHE_ENABLED:
            self.response_cache = ResponseCache(
                similarity_threshold=RESPONSE_CACHE_SIMILARITY,
                max_cache_size=RESPONSE_CACHE_SIZE,
                ttl_seconds=RESPONSE_CACHE_TTL,
                featured_ttl_seconds=RESPONSE_CACHE_FEATURED_TTL,
            )
            logger.info("Response cache enabled")
        else:
            self.response_cache = None
            logger.info("Response cache disabled")

        logger.info("CARE Bot initialized successfully")

    def process_query(
        self,
        user_query: str,
        scenario_category: Optional[str] = None,
        check_crisis: bool = True,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process user query through the RAG pipeline.

        Args:
            user_query:        User's question or message
            scenario_category: Optional scenario category for document filtering
            check_crisis:      Whether to run crisis detection
            session_id:        Session ID for DynamoDB conversation history

        Returns:
            Dictionary containing response and metadata
        """
        logger.info(f"Processing query: '{user_query[:50]}...'")

        # Step 1: Keyword Crisis Detection
        keyword_crisis = {"is_crisis": False, "keyword_triggered": False, "model_triggered": False}

        if check_crisis:
            keyword_crisis = self.crisis_detector.analyze(user_query)

            if keyword_crisis["is_crisis"]:
                logger.warning(
                    f"Crisis keyword detected — "
                    f"keyword: {keyword_crisis['keyword_triggered']}"
                )

        # Step 1.5: Check response cache (skip if crisis detected)
        if self.response_cache and not keyword_crisis["is_crisis"]:
            cached = self.response_cache.get(user_query)
            if cached:
                logger.info("Returning cached response")
                return cached

        # Step 2: Retrieval
        retrieved_docs = []
        try:
            if scenario_category:
                retrieved_docs = self.retriever.retrieve_by_scenario(
                    user_query,
                    scenario_category
                )
            else:
                retrieved_docs = self.retriever.retrieve(user_query)

            logger.info(f"Retrieved {len(retrieved_docs)} documents")

        except Exception as e:
            logger.error(f"Error in retrieval: {str(e)}")

        # Step 3: Construct Prompt
        if scenario_category:
            prompt = self.prompt_templates.get_scenario_specific_prompt(
                user_query,
                retrieved_docs,
                scenario_category
            )
        else:
            prompt = self.prompt_templates.get_rag_prompt(
                user_query,
                retrieved_docs
            )

        # Step 4: If keywords triggered, prepend crisis emphasis
        if keyword_crisis["is_crisis"]:
            prompt = _CRISIS_EMPHASIS + prompt

        # Step 5: Generate Response (LLM also assesses crisis via JSON)
        llm_response = self.llm_handler.generate_response(
            prompt,
            user_query=user_query,
            session_id=session_id,
        )
        response_text = llm_response["text"]

        # Step 6: Merge crisis signals
        # Crisis if keywords OR LLM detected it
        final_is_crisis = keyword_crisis["is_crisis"] or llm_response.get("is_crisis", False)

        logger.info(f"Generated response of length: {len(response_text)}")

        # Step 7: Build result
        result = {
            "response":           response_text,
            "is_crisis":          final_is_crisis,
            "keyword_triggered":  keyword_crisis.get("keyword_triggered", False),
            "model_triggered":    llm_response.get("is_crisis", False),
            "num_docs_retrieved": len(retrieved_docs),
            "blocked":            llm_response.get("blocked", False),
            "retrieved_docs": [
                {
                    "text":     doc["text"][:200] + "...",
                    "source":   doc["metadata"].get("source", "Unknown"),
                    "page":     doc["metadata"].get("page", "N/A"),
                    "distance": doc["distance"]
                }
                for doc in retrieved_docs[:3]
            ],
        }

        log_interaction(
            logger,
            user_query,
            response_text,
            {
                "crisis":          result["is_crisis"],
                "docs_retrieved":  result["num_docs_retrieved"],
                "scenario":        scenario_category,
            }
        )

        # Step 8: Cache response (if enabled and not crisis)
        if self.response_cache:
            self.response_cache.put(user_query, result)

        return result

    def clear_conversation(self, session_id: Optional[str] = None) -> None:
        """Clear conversation history for a session."""
        self.llm_handler.clear_history(session_id=session_id)
        logger.info(f"Conversation history cleared for session {session_id or 'all'}")

    def initialize_vector_store(self, force_rebuild: bool = True) -> None:
        """
        Initialize vector store with documents.

        Args:
            force_rebuild: Whether to rebuild vector store from scratch
        """
        logger.info("Initializing vector store...")

        stats = self.vector_store.get_collection_stats()

        if stats["document_count"] > 0 and not force_rebuild:
            logger.info(f"Vector store already has {stats['document_count']} documents")
            return

        # On Lambda, PDFs aren't available — vectorstore must come from S3
        if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            logger.warning("Lambda environment: cannot rebuild vectorstore (no PDFs). Upload via S3.")
            return

        if force_rebuild:
            logger.info("Rebuilding vector store from scratch...")
            self.vector_store.reset_collection()

        doc_processor = DocumentProcessor()
        documents = doc_processor.process_all_documents()
        self.vector_store.add_documents(documents)

        logger.info(f"Vector store initialized with {len(documents)} documents")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the bot."""
        vector_stats = self.vector_store.get_collection_stats()
        history_stats = self.llm_handler.get_history_summary()

        return {
            "vector_store":        vector_stats,
            "retriever_top_k":     self.retriever.top_k,
            "llm_model":           self.llm_handler.model_name,
            "crisis_keywords":     len(CRISIS_KEYWORDS),
            "conversation_history": history_stats,
        }


