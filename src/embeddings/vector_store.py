"""
Vector store management using ChromaDB
Supports both local and AWS Lambda environments
"""
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import os
import tempfile
from config.settings import VECTORSTORE_DIR, EMBEDDING_MODEL, TOP_K
from src.utils.logger import get_logger

logger = get_logger(__name__)


class VectorStore:
    """Manage vector storage and retrieval using ChromaDB"""
    
    def __init__(self, collection_name: str = "care_bot_documents"):
        self.collection_name = collection_name
        
        # Determine vectorstore path (handle Lambda environment)
        vectorstore_path = self._get_vectorstore_path()
        
        logger.info(f"Using vectorstore path: {vectorstore_path}")
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(vectorstore_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedding function
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
        
        # Get or create collection
        self.collection = self._get_or_create_collection()
        
        logger.info(f"Initialized VectorStore with collection: {collection_name}")
    
    def _get_vectorstore_path(self) -> str:
        """
        Get appropriate vectorstore path for environment
        Uses /tmp for Lambda, or local path for development
        """
        # Check if running in Lambda
        if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            # In Lambda, use /tmp (ephemeral storage)
            path = "/tmp/vectorstore"
            os.makedirs(path, exist_ok=True)
            logger.info("Running in Lambda - using /tmp for vectorstore")
            return path
        else:
            # Local development - use configured path
            vectorstore_path = VECTORSTORE_DIR
            if isinstance(vectorstore_path, str):
                os.makedirs(vectorstore_path, exist_ok=True)
                return vectorstore_path
            else:
                # It's a Path object
                vectorstore_path.mkdir(parents=True, exist_ok=True)
                return str(vectorstore_path)
    
    def _get_or_create_collection(self):
        """Get existing collection or create new one"""
        try:
            collection = self.client.get_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
            logger.info(f"Loaded existing collection: {self.collection_name}")
        except:
            collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"description": "CARE Bot trauma-informed documents"}
            )
            logger.info(f"Created new collection: {self.collection_name}")
        
        return collection
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Add documents to the vector store"""
        logger.info(f"Adding {len(documents)} documents to vector store")
        
        try:
            # Prepare data for ChromaDB
            ids = [f"doc_{i}" for i in range(len(documents))]
            texts = [doc["text"] for doc in documents]
            metadatas = [doc["metadata"] for doc in documents]
            
            # Add to collection
            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )
            
            logger.info(f"Successfully added {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            raise
    
    def similarity_search(self, 
                         query: str, 
                         k: int = TOP_K,
                         filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Perform similarity search on the vector store
        
        Args:
            query: Search query text
            k: Number of results to return
            filter_dict: Optional metadata filters
        
        Returns:
            List of documents with metadata and similarity scores
        """
        logger.info(f"Performing similarity search for: '{query[:50]}...' with k={k}")
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=k,
                where=filter_dict
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "text": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i],
                    "id": results['ids'][0][i]
                })
            
            logger.info(f"Found {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in similarity search: {str(e)}")
            raise
    
    def similarity_search_with_score(self,
                                    query: str,
                                    k: int = TOP_K,
                                    score_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        Perform similarity search and filter by score threshold
        
        Args:
            query: Search query
            k: Number of results
            score_threshold: Minimum similarity score (lower distance = higher similarity)
        
        Returns:
            Filtered results above threshold
        """
        results = self.similarity_search(query, k)
        
        # Filter by threshold (ChromaDB returns distances, lower is better)
        # Convert distance to similarity score (1 - normalized_distance)
        filtered_results = [
            r for r in results 
            if r['distance'] <= score_threshold
        ]
        
        logger.info(f"Filtered to {len(filtered_results)} results above threshold")
        return filtered_results
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        count = self.collection.count()
        
        return {
            "collection_name": self.collection_name,
            "document_count": count,
            "embedding_model": EMBEDDING_MODEL
        }
    
    def reset_collection(self) -> None:
        """Delete and recreate the collection (use with caution!)"""
        logger.warning(f"Resetting collection: {self.collection_name}")
        
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self._get_or_create_collection()
            logger.info("Collection reset successfully")
        except Exception as e:
            logger.error(f"Error resetting collection: {str(e)}")
            raise


if __name__ == "__main__":
    # Test vector store
    vector_store = VectorStore()
    
    # Get stats
    stats = vector_store.get_collection_stats()
    print(f"\nVector Store Stats:")
    print(f"Collection: {stats['collection_name']}")
    print(f"Documents: {stats['document_count']}")
    print(f"Embedding Model: {stats['embedding_model']}")
