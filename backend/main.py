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
from config.settings import TOP_K

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

=====================================================

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

        # ── Step 1: Keyword Crisis Detection (fast, free) ──────────────────
        keyword_crisis = {"is_crisis": False, "keyword_triggered": False, "model_triggered": False}

        if check_crisis:
            keyword_crisis = self.crisis_detector.analyze(user_query)

            if keyword_crisis["is_crisis"]:
                logger.warning(
                    f"Crisis keyword detected — "
                    f"keyword: {keyword_crisis['keyword_triggered']}"
                )

        # ── Step 2: Retrieval ──────────────────────────────────────────────
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

        # ── Step 3: Construct Prompt ──────────────────────────────────────
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

        # ── Step 4: If keywords triggered, prepend crisis emphasis ────────
        if keyword_crisis["is_crisis"]:
            prompt = _CRISIS_EMPHASIS + prompt

        # ── Step 5: Generate Response (LLM also assesses crisis via JSON) ─
        llm_response = self.llm_handler.generate_response(
            prompt,
            user_query=user_query,
            session_id=session_id,
        )
        response_text = llm_response["text"]

        # ── Step 6: Merge crisis signals ──────────────────────────────────
        # Crisis if keywords OR LLM detected it
        final_is_crisis = keyword_crisis["is_crisis"] or llm_response.get("is_crisis", False)

        logger.info(f"Generated response of length: {len(response_text)}")

        # ── Step 7: Build result ──────────────────────────────────────────
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

    def _get_fallback_response(self) -> str:
        """Get fallback response for errors."""
        return (
            "I apologize, but I'm having trouble responding right now.\n\n"
            "For immediate support, please reach out to:\n"
            "- **National Sexual Assault Hotline**: 1-800-656-HOPE (4673)\n"
            "- **Crisis Text Line**: Text \"HELLO\" to 741741\n"
            "- **988 Suicide & Crisis Lifeline**: Call or text 988\n\n"
            "Your forensic nurse or advocate can also help connect you with "
            "local resources and support."
        )


def main():
    """Main function to run the CARE Bot"""
    print("=" * 80)
    print("CARE Bot - Trauma-Informed Support Chatbot")
    print("=" * 80)

    bot = CAREBot()

    stats = bot.get_stats()
    print(f"\nBot Stats:")
    print(f"  Documents in vector store: {stats['vector_store']['document_count']}")
    print(f"  LLM Model: {stats['llm_model']}")
    print(f"  Retrieval top_k: {stats['retriever_top_k']}")

    if stats['vector_store']['document_count'] == 0:
        print("\nVector store is empty. Initializing with documents...")
        bot.initialize_vector_store()
        print("Vector store initialized!")

    print("\n" + "=" * 80)
    print("You can now chat with CARE Bot.")
    print("\nCommands:")
    print("  'quit'    - Exit")
    print("  'stats'   - Show bot statistics")
    print("  'menu'    - Show help categories again")
    print("  'clear'   - Clear conversation history")
    print("  'history' - Show conversation history info")
    print("=" * 80 + "\n")

    show_menu()

    pending_scenario = None

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            if user_input.lower() == 'quit':
                print("\nThank you for using CARE Bot. Take care of yourself.")
                break

            if user_input.lower() == 'stats':
                print(f"\n{bot.get_stats()}")
                continue

            if user_input.lower() == 'menu':
                pending_scenario = None
                show_menu()
                continue

            if user_input.lower() == 'clear':
                bot.clear_conversation()
                pending_scenario = None
                print("\nConversation history cleared. Starting fresh.")
                continue

            if user_input.lower() == 'history':
                history = bot.llm_handler.get_history_summary()
                print(f"\nConversation History:")
                print(f"  Turns: {history['total_turns']}/{history['max_turns']}")
                print(f"  Messages: {history['messages']}")
                continue

            scenario = parse_category_choice(user_input)

            if scenario == "show_menu":
                pending_scenario = parse_category_from_number(user_input.strip())
                continue

            active_scenario = scenario if scenario else pending_scenario

            result = bot.process_query(user_input, scenario_category=active_scenario)

            print(f"\nCARE Bot: {result['response']}")

            if result.get("is_crisis"):
                print(f"\n[Crisis Detected — keyword: {result.get('keyword_triggered')}, llm: {result.get('model_triggered')}]")

            if active_scenario:
                print(f"\n[Category: {get_category_name(active_scenario)}]")

            print(f"[Retrieved {result['num_docs_retrieved']} relevant documents]")

        except KeyboardInterrupt:
            print("\n\nInterrupted. Exiting...")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            print(f"\nAn error occurred: {str(e)}")


def show_menu():
    """Display the help category menu."""
    print("\n" + "=" * 80)
    print("What type of help are you looking for?")
    print("=" * 80)
    print("\n1. Medical Follow-Up")
    print("   (STI/HIV testing, medical appointments, prophylaxis)")
    print("\n2. Mental Health Support")
    print("   (Counseling, anxiety, sleep issues, trauma support)")
    print("\n3. Practical & Social Needs")
    print("   (Housing, transportation, financial assistance)")
    print("\n4. Legal & Advocacy")
    print("   (Legal help, protection orders, reporting options)")
    print("\n5. Delayed Follow-Up")
    print("   (It's been a while, not sure if it still matters)")
    print("\n6. General Help")
    print("   (Not sure / just want to talk)")
    print("=" * 80)
    print("\nYou can:")
    print("  - Type a number (1-6) to select a category")
    print("  - Or just type your question directly (uses general help)")
    print("=" * 80)


def parse_category_from_number(number: str) -> Optional[str]:
    """Convert a number selection to a scenario category."""
    category_map = {
        "1": "immediate_followup",
        "2": "mental_health",
        "3": "practical_social",
        "4": "legal_advocacy",
        "5": "delayed_ambivalent",
        "6": None,
    }
    return category_map.get(number)


def parse_category_choice(user_input: str) -> Optional[str]:
    """Parse user input to detect category selection."""
    category_map = {
        "1": "immediate_followup",
        "2": "mental_health",
        "3": "practical_social",
        "4": "legal_advocacy",
        "5": "delayed_ambivalent",
        "6": None,
    }

    stripped = user_input.strip()

    if stripped in category_map:
        category = category_map[stripped]
        category_name = get_category_name(category) if category else "General Help"
        print(f"\n→ Selected: {category_name}")
        print("→ Please type your question:")
        return "show_menu"

    if len(stripped) > 1 and stripped[0] in category_map:
        return category_map[stripped[0]]

    return None


def get_category_name(scenario: Optional[str]) -> str:
    """Get display name for scenario category."""
    names = {
        "immediate_followup": "Medical Follow-Up",
        "mental_health":      "Mental Health Support",
        "practical_social":   "Practical & Social Needs",
        "legal_advocacy":     "Legal & Advocacy",
        "delayed_ambivalent": "Delayed Follow-Up",
        None:                 "General Help",
    }
    return names.get(scenario, "General Help")


if __name__ == "__main__":
    main()
