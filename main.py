"""
CARE Bot - Trauma-Informed RAG Chatbot
Main application orchestrating the RAG pipeline
"""
from typing import Dict, Any, Optional
from src.embeddings.document_processor import DocumentProcessor
from src.embeddings.vector_store import VectorStore
from src.retrieval.retriever import Retriever
from src.generation.prompt_templates import PromptTemplates
from src.generation.llm_handler import LLMHandler
from src.safety.crisis_detector import CrisisDetector
from src.utils.logger import get_logger, log_interaction
from config.settings import TOP_K

logger = get_logger(__name__)


class CAREBot:
    """Main CARE Bot application class"""
    
    def __init__(self, top_k: int = TOP_K):
        """
        Initialize CARE Bot with all components
        
        Args:
            top_k: Number of documents to retrieve for context
        """
        logger.info("Initializing CARE Bot...")
        
        # Initialize components
        self.vector_store = VectorStore()
        self.retriever = Retriever(self.vector_store, top_k=top_k)
        self.llm_handler = LLMHandler()
        self.prompt_templates = PromptTemplates()
        self.crisis_detector = CrisisDetector()
        
        logger.info("CARE Bot initialized successfully")
    
    def process_query(self, 
                     user_query: str, 
                     scenario_category: Optional[str] = None,
                     check_crisis: bool = True) -> Dict[str, Any]:
        """
        Process user query through the RAG pipeline
        
        Args:
            user_query: User's question or message
            scenario_category: Optional scenario category for filtering
            check_crisis: Whether to check for crisis indicators
        
        Returns:
            Dictionary containing response and metadata
        """
        logger.info(f"Processing query: '{user_query[:50]}...'")
        
        # Step 1: Crisis Detection
        crisis_result = None
        if check_crisis:
            crisis_result = self.crisis_detector.detect_crisis(user_query)
            
            if crisis_result["is_crisis"]:
                logger.warning(f"Crisis detected")
                
                # Return crisis response immediately for any crisis
                crisis_response = self.crisis_detector.get_crisis_response()
                
                return {
                    "response": crisis_response,
                    "num_docs_retrieved": 0,
                    "is_crisis": True,
                    "retrieved_docs": [],
                    "source": "crisis_protocol"
                }
        
        # Step 2: Retrieval
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
            retrieved_docs = []
        
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
        
        # If crisis was detected but we're still generating a response, add crisis resources
        if crisis_result and crisis_result["is_crisis"]:
            crisis_addendum = f"\n\nIMPORTANT: The user may be in distress. Include crisis resources in your response:\n{self.crisis_detector.get_crisis_response()}"
            prompt += crisis_addendum
        
        # Step 4: Generate Response
        try:
            llm_response = self.llm_handler.generate_response(prompt)
            response_text = llm_response["text"]
            
            logger.info(f"Generated response of length: {len(response_text)}")
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            response_text = self._get_fallback_response()
        
        # Step 5: Construct final response
        result = {
            "response": response_text,
            "is_crisis": crisis_result["is_crisis"] if crisis_result else False,
            "retrieved_docs": [
                {
                    "text": doc["text"][:200] + "...",
                    "source": doc["metadata"].get("source", "Unknown"),
                    "page": doc["metadata"].get("page", "N/A"),
                    "distance": doc["distance"]
                }
                for doc in retrieved_docs[:3]  # Include top 3 for transparency
            ],
            "num_docs_retrieved": len(retrieved_docs),
            "blocked": llm_response.get("blocked", False) if isinstance(llm_response, dict) else False
        }
        
        # Log interaction (privacy-preserving)
        log_interaction(
            logger,
            user_query,
            response_text,
            {
                "crisis": result["is_crisis"],
                "docs_retrieved": result["num_docs_retrieved"],
                "scenario": scenario_category
            }
        )
        
        return result
    
    def _get_fallback_response(self) -> str:
        """Get fallback response for errors"""
        return """I apologize, but I'm having trouble responding right now. 

For immediate support, please reach out to:
• **National Sexual Assault Hotline**: 1-800-656-HOPE (4673)
• **Crisis Text Line**: Text "HELLO" to 741741
• **988 Suicide & Crisis Lifeline**: Call or text 988

Your forensic nurse or advocate can also help connect you with local resources and support."""
    
    def initialize_vector_store(self, force_rebuild: bool = False) -> None:
        """
        Initialize vector store with documents
        
        Args:
            force_rebuild: Whether to rebuild vector store from scratch
        """
        logger.info("Initializing vector store...")
        
        # Check if vector store already has documents
        stats = self.vector_store.get_collection_stats()
        
        if stats["document_count"] > 0 and not force_rebuild:
            logger.info(f"Vector store already has {stats['document_count']} documents")
            return
        
        if force_rebuild:
            logger.info("Rebuilding vector store from scratch...")
            self.vector_store.reset_collection()
        
        # Process documents
        doc_processor = DocumentProcessor()
        documents = doc_processor.process_all_documents()
        
        # Add to vector store
        self.vector_store.add_documents(documents)
        
        logger.info(f"Vector store initialized with {len(documents)} documents")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the bot"""
        vector_stats = self.vector_store.get_collection_stats()
        
        return {
            "vector_store": vector_stats,
            "retriever_top_k": self.retriever.top_k,
            "llm_model": self.llm_handler.model_name,
            "crisis_keywords": len(self.crisis_detector.crisis_keywords)
        }


def main():
    """Main function to run the CARE Bot"""
    print("="*80)
    print("CARE Bot - Trauma-Informed Support Chatbot")
    print("="*80)
    
    # Initialize bot
    bot = CAREBot()
    
    # Check if vector store needs initialization
    stats = bot.get_stats()
    print(f"\nBot Stats:")
    print(f"  Documents in vector store: {stats['vector_store']['document_count']}")
    print(f"  LLM Model: {stats['llm_model']}")
    print(f"  Retrieval top_k: {stats['retriever_top_k']}")
    
    if stats['vector_store']['document_count'] == 0:
        print("\nVector store is empty. Initializing with documents...")
        bot.initialize_vector_store()
        print("Vector store initialized!")
    
    # Interactive loop
    print("\n" + "="*80)
    print("You can now chat with CARE Bot.")
    print("\nCommands:")
    print("  'quit' - Exit")
    print("  'stats' - Show bot statistics")
    print("  'menu' - Show help categories again")
    print("="*80 + "\n")
    
    # Show initial menu
    show_menu()
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                print("\nThank you for using CARE Bot. Take care of yourself.")
                break
            
            if user_input.lower() == 'stats':
                stats = bot.get_stats()
                print(f"\n{stats}")
                continue
            
            if user_input.lower() == 'menu':
                show_menu()
                continue
            
            # Check if user selected a category number
            scenario = parse_category_choice(user_input)
            
            if scenario == "show_menu":
                # User entered just a number, show what they selected
                continue
            
            # Process query with detected scenario (or None for generic)
            result = bot.process_query(user_input, scenario_category=scenario)
            
            # Display response
            print(f"\nCARE Bot: {result['response']}")
            
            # Show metadata
            if result.get("is_crisis"):
                print(f"\n[Crisis Detected]")
            
            if scenario:
                print(f"\n[Category: {get_category_name(scenario)}]")
            
            print(f"[Retrieved {result['num_docs_retrieved']} relevant documents]")
            
        except KeyboardInterrupt:
            print("\n\nInterrupted. Exiting...")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            print(f"\nAn error occurred: {str(e)}")


def show_menu():
    """Display the help category menu"""
    print("\n" + "="*80)
    print("What type of help are you looking for?")
    print("="*80)
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
    print("="*80)
    print("\nYou can:")
    print("  • Type a number (1-6) to select a category")
    print("  • Or just type your question directly (uses general help)")
    print("="*80)


def parse_category_choice(user_input: str) -> Optional[str]:
    """
    Parse user input to detect category selection
    
    Args:
        user_input: User's input text
    
    Returns:
        Scenario category string, None for generic, or "show_menu" if just number
    """
    # Category mapping
    category_map = {
        "1": "immediate_followup",
        "2": "mental_health",
        "3": "practical_social",
        "4": "legal_advocacy",
        "5": "delayed_ambivalent",
        "6": None  # Explicit choice for generic
    }
    
    # Check if input is just a number
    stripped = user_input.strip()
    if stripped in category_map:
        category = category_map[stripped]
        category_name = get_category_name(category) if category else "General Help"
        print(f"\n→ Selected: {category_name}")
        print("→ Please type your question:")
        return "show_menu"  # Signal to wait for actual question
    
    # Check if input starts with a number choice
    if len(stripped) > 1 and stripped[0] in category_map:
        # E.g., "2 I can't sleep"
        choice = stripped[0]
        category = category_map[choice]
        # Strip the number from the input
        # This is handled by returning the category; caller will use original input
        return category
    
    # Otherwise, use generic RAG (no specific category)
    return None


def get_category_name(scenario: Optional[str]) -> str:
    """Get display name for scenario category"""
    names = {
        "immediate_followup": "Medical Follow-Up",
        "mental_health": "Mental Health Support",
        "practical_social": "Practical & Social Needs",
        "legal_advocacy": "Legal & Advocacy",
        "delayed_ambivalent": "Delayed Follow-Up",
        None: "General Help"
    }
    return names.get(scenario, "General Help")


if __name__ == "__main__":
    main()