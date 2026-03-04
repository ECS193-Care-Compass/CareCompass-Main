"""
Retrieval system for RAG pipeline
"""
from typing import List, Dict, Any, Optional
from src.embeddings.vector_store import VectorStore
from config.settings import TOP_K, SIMILARITY_THRESHOLD
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Retriever:
    """Handle document retrieval for RAG pipeline"""
    
    def __init__(self, vector_store: VectorStore, top_k: int = TOP_K):
        """
        Initialize retriever
        
        Args:
            vector_store: VectorStore instance
            top_k: Number of documents to retrieve
        """
        self.vector_store = vector_store
        self.top_k = top_k
        logger.info(f"Initialized Retriever with top_k={top_k}")
    
    def retrieve(self, 
                query: str, 
                k: Optional[int] = None,
                filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query
        
        Args:
            query: User query
            k: Number of results (defaults to self.top_k)
            filter_metadata: Optional metadata filters
        
        Returns:
            List of retrieved documents with scores
        """
        k = k or self.top_k
        
        logger.info(f"Retrieving documents for query: '{query[:50]}...'")
        
        try:
            results = self.vector_store.similarity_search(
                query=query,
                k=k,
                filter_dict=filter_metadata
            )
            
            logger.info(f"Retrieved {len(results)} documents")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in retrieval: {str(e)}")
            return []
    
    def retrieve_with_threshold(self,
                               query: str,
                               k: Optional[int] = None,
                               threshold: float = SIMILARITY_THRESHOLD) -> List[Dict[str, Any]]:
        """
        Retrieve documents above a similarity threshold
        
        Args:
            query: User query
            k: Number of results
            threshold: Similarity threshold
        
        Returns:
            Filtered documents above threshold
        """
        results = self.retrieve(query, k)
        
        # Filter by threshold (lower distance = more similar)
        filtered = [r for r in results if r['distance'] <= threshold]
        
        logger.info(f"Filtered to {len(filtered)} documents above threshold {threshold}")
        
        return filtered
    
    def retrieve_by_scenario(self,
                            query: str,
                            scenario_category: str,
                            k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve documents for a specific scenario category
        Falls back to regular retrieval if no scenario-tagged documents found
        
        Args:
            query: User query
            scenario_category: Scenario category to filter by
            k: Number of results
        
        Returns:
            Scenario-filtered documents, or general results as fallback
        """
        filter_dict = {"scenario_category": scenario_category}
        
        results = self.retrieve(query, k, filter_metadata=filter_dict)
        
        # Fallback: if no scenario-tagged docs found, use regular retrieval
        if not results:
            logger.info(f"No documents with scenario '{scenario_category}', falling back to general retrieval")
            results = self.retrieve(query, k)
        
        return results
    
    def retrieve_foundational_content(self,
                                     query: str,
                                     k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve from foundational trauma-informed care framework documents
        
        Args:
            query: User query
            k: Number of results
        
        Returns:
            Documents from foundational sources
        """
        filter_dict = {"document_type": "foundational_framework"}
        
        return self.retrieve(query, k, filter_metadata=filter_dict)
    
    def format_context_for_prompt(self, documents: List[Dict[str, Any]]) -> str:
        """
        Format retrieved documents into context string for prompt
        
        Args:
            documents: Retrieved documents
        
        Returns:
            Formatted context string
        """
        if not documents:
            return "No specific context found. Please provide general guidance based on trauma-informed principles."
        
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            source = doc['metadata'].get('source', 'Unknown')
            page = doc['metadata'].get('page', 'N/A')
            text = doc['text']
            
            context_parts.append(
                f"[Document {i}]\n"
                f"Source: {source} (Page {page})\n"
                f"Content: {text}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    def get_retrieval_stats(self, query: str, k: Optional[int] = None) -> Dict[str, Any]:
        """
        Get statistics about retrieval for a query
        
        Args:
            query: User query
            k: Number of results
        
        Returns:
            Retrieval statistics
        """
        results = self.retrieve(query, k)
        
        if not results:
            return {
                "query": query,
                "retrieved_count": 0,
                "avg_distance": None,
                "sources": []
            }
        
        distances = [r['distance'] for r in results]
        sources = list(set([r['metadata'].get('source', 'Unknown') for r in results]))
        
        return {
            "query": query,
            "retrieved_count": len(results),
            "avg_distance": sum(distances) / len(distances),
            "min_distance": min(distances),
            "max_distance": max(distances),
            "sources": sources
        }


if __name__ == "__main__":
    # Test retriever
    print("Initializing vector store and retriever...")
    vector_store = VectorStore()
    retriever = Retriever(vector_store)
    
    # Test query
    test_query = "What follow-up care do I need after a forensic exam?"
    
    print(f"\nTest Query: {test_query}")
    
    # Get stats
    stats = retriever.get_retrieval_stats(test_query, k=3)
    print(f"\nRetrieval Stats:")
    print(f"  Retrieved: {stats['retrieved_count']} documents")
    
    if stats['retrieved_count'] > 0:
        print(f"  Avg Distance: {stats['avg_distance']:.4f}")
        print(f"  Sources: {', '.join(stats['sources'])}")
        
        # Get actual results
        results = retriever.retrieve(test_query, k=3)
        print(f"\nSample Result:")
        print(f"  Text: {results[0]['text'][:200]}...")
        print(f"  Distance: {results[0]['distance']:.4f}")