"""
Vector store management using ChromaDB
Supports both local and AWS Lambda environments
Uses Google Gemini API for embeddings
"""
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from google import genai
import os
import time
import tempfile
import zipfile
from config.settings import VECTORSTORE_DIR, EMBEDDING_MODEL, TOP_K, GOOGLE_API_KEY
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GeminiEmbeddingFunction(EmbeddingFunction):
    """ChromaDB embedding function using Google Gemini API"""

    def __init__(self, api_key: str = GOOGLE_API_KEY, model_name: str = EMBEDDING_MODEL):
        if not api_key:
            raise ValueError("GOOGLE_API_KEY must be set for Gemini embeddings")
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        """Embed a list of documents using Gemini embedding API with rate limiting"""
        results = []
        batch_size = 100
        total_batches = (len(input) + batch_size - 1) // batch_size

        for batch_idx, i in enumerate(range(0, len(input), batch_size)):
            batch = input[i : i + batch_size]

            # Retry with exponential backoff on rate limit errors
            for attempt in range(5):
                try:
                    response = self._client.models.embed_content(
                        model=self._model_name,
                        contents=batch,
                    )
                    results.extend([list(e.values) for e in response.embeddings])
                    break
                except Exception as e:
                    if "429" in str(e) and attempt < 4:
                        wait = 2 ** attempt * 10  # 10s, 20s, 40s, 80s
                        logger.warning(f"Rate limited, waiting {wait}s (attempt {attempt + 1}/5)")
                        time.sleep(wait)
                    else:
                        raise

            if batch_idx < total_batches - 1:
                logger.info(f"Embedded batch {batch_idx + 1}/{total_batches}, pausing for rate limit...")
                time.sleep(1)

        return results


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
        self.embedding_function = GeminiEmbeddingFunction()

        # Get or create collection
        self.collection = self._get_or_create_collection()

        logger.info(f"Initialized VectorStore with collection: {collection_name}")

    def _get_vectorstore_path(self) -> str:
        """
        Get appropriate vectorstore path for environment
        Uses /tmp for Lambda (with S3 restore), or local path for development
        """
        if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            path = "/tmp/vectorstore"
            os.makedirs(path, exist_ok=True)
            logger.info("Running in Lambda - using /tmp for vectorstore")

            # Download vectorstore from S3 if /tmp is empty
            if not os.path.exists(os.path.join(path, "chroma.sqlite3")):
                self._restore_from_s3(path)

            return path
        else:
            vectorstore_path = VECTORSTORE_DIR
            if isinstance(vectorstore_path, str):
                os.makedirs(vectorstore_path, exist_ok=True)
                return vectorstore_path
            else:
                vectorstore_path.mkdir(parents=True, exist_ok=True)
                return str(vectorstore_path)

    def _restore_from_s3(self, target_path: str) -> None:
        """Download and extract vectorstore zip from S3 on Lambda cold start"""
        try:
            import boto3
            bucket = os.environ.get("S3_VECTORDB_BUCKET")
            if not bucket:
                logger.warning("S3_VECTORDB_BUCKET not set, skipping vectorstore restore")
                return

            s3 = boto3.client("s3")
            zip_key = "vectorstore/vectorstore.zip"
            zip_path = "/tmp/vectorstore.zip"

            logger.info(f"Downloading vectorstore from s3://{bucket}/{zip_key}")
            s3.download_file(bucket, zip_key, zip_path)

            logger.info(f"Extracting vectorstore to {target_path}")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(target_path)

            os.remove(zip_path)
            logger.info("Vectorstore restored from S3 successfully")

        except Exception as e:
            logger.warning(f"Failed to restore vectorstore from S3: {e}")

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


